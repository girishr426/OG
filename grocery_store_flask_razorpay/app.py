from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3, os, hmac, hashlib
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image

# Optional: Razorpay SDK (install via pip)
try:
    import razorpay
except ImportError:
    razorpay = None

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = os.environ.get('APP_SECRET_KEY', 'change-this-secret-key')
DB_PATH = 'store.db'

# Session configuration - Keep admin logged in
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)  # 30 days session expiry
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True if using HTTPS in production
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access to session cookie
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection

# Image upload configuration
UPLOAD_FOLDER = 'static/product_images'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['MAX_CONTENT_LENGTH'] = MAX_IMAGE_SIZE


RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET')
RAZORPAY_WEBHOOK_SECRET = os.environ.get('RAZORPAY_WEBHOOK_SECRET')

client = None
if razorpay and RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_product_image(file, product_id):
    """Save and optimize product image"""
    if not file or file.filename == '':
        return None
    
    if not allowed_file(file.filename):
        flash('Invalid file type. Allowed: JPG, PNG, GIF', 'error')
        return None
    
    try:
        # Save with secure filename
        filename = secure_filename(f"product_{product_id}_{datetime.now().timestamp()}.jpg")
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        # Open, optimize and save image
        img = Image.open(file)
        img = img.convert('RGB')
        img.thumbnail((400, 400))
        img.save(filepath, 'JPEG', quality=85, optimize=True)
        
        return f'product_images/{filename}'
    except Exception as e:
        flash(f'Error uploading image: {str(e)}', 'error')
        return None


########################
# Database utilities
########################

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            stock INTEGER DEFAULT 0,
            estimated_delivery_days INTEGER,
            estimated_delivery_date TEXT,
            image_path TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            email TEXT,
            phone TEXT,
            address TEXT,
            city TEXT,
            pincode TEXT,
            total_amount REAL,
            payment_status TEXT,
            created_at TEXT,
            estimated_delivery_date TEXT,
            razorpay_order_id TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            unit_price REAL,
            FOREIGN KEY(order_id) REFERENCES orders(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            phone TEXT,
            address TEXT,
            city TEXT,
            pincode TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT
        )
    ''')
    # Seed default admin if not exists
    cur.execute('SELECT COUNT(*) as c FROM admin_users')
    if cur.fetchone()['c'] == 0:
        cur.execute('INSERT INTO admin_users (username, password_hash) VALUES (?, ?)', (
            'admin', generate_password_hash('admin123')
        ))
    
    # Seed sample products if none
    cur.execute('SELECT COUNT(*) as c FROM products')
    if cur.fetchone()['c'] == 0:
        sample = [
            ('Basmati Rice 5kg', 'Premium aged basmati rice', 649.0, 50, 2, None, 'product_images/rice.jpg'),
            ('Fresh Milk 1L', 'Pasteurized toned milk', 58.0, 100, 1, None, 'product_images/milk.jpg'),
            ('Organic Eggs (12)', 'Free-range organic eggs', 110.0, 80, 2, None, 'product_images/eggs.jpg'),
            ('Tomatoes 1kg', 'Farm-fresh tomatoes', 35.0, 150, 1, None, 'product_images/tomatoes.jpg'),
        ]
        cur.executemany('INSERT INTO products (name, description, price, stock, estimated_delivery_days, estimated_delivery_date, image_path) VALUES (?, ?, ?, ?, ?, ?, ?)', sample)
    conn.commit()
    conn.close()


# Initialize database on first request
_db_initialized = False

@app.before_request
def setup():
    global _db_initialized
    if not _db_initialized:
        init_db()
        _db_initialized = True

########################
# Helper functions
########################

def calculate_estimated_date(product_row):
    exp_date = product_row['estimated_delivery_date']
    if exp_date:
        try:
            datetime.strptime(exp_date, '%Y-%m-%d')
            return exp_date
        except Exception:
            return exp_date
    days = product_row['estimated_delivery_days']
    if days:
        return (datetime.now() + timedelta(days=int(days))).strftime('%Y-%m-%d')
    return (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')


def cart_total(cart_items):
    return sum(item['price'] * item['quantity'] for item in cart_items)

########################
# Public routes
########################

@app.route('/')
def index():
    conn = get_db()
    products = conn.execute('SELECT * FROM products ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('index.html', products=products)


@app.route('/product/<int:pid>')
def product_detail(pid):
    conn = get_db()
    product = conn.execute('SELECT * FROM products WHERE id=?', (pid,)).fetchone()
    conn.close()
    if not product:
        flash('Product not found', 'error')
        return redirect(url_for('index'))
    return render_template('product_detail.html', product=product, est_date=calculate_estimated_date(product))


@app.route('/add_to_cart/<int:pid>')
def add_to_cart(pid):
    conn = get_db()
    p = conn.execute('SELECT * FROM products WHERE id=?', (pid,)).fetchone()
    conn.close()
    if not p:
        flash('Product not found', 'error')
        return redirect(url_for('index'))
    cart = session.get('cart', [])
    found = False
    for item in cart:
        if item['id'] == pid:
            item['quantity'] += 1
            found = True
            break
    if not found:
        cart.append({'id': p['id'], 'name': p['name'], 'price': float(p['price']), 'quantity': 1})
    session['cart'] = cart
    flash('Added to cart', 'success')
    return redirect(url_for('index'))


@app.route('/cart', methods=['GET', 'POST'])
def cart():
    if request.method == 'POST':
        cart = session.get('cart', [])
        for item in cart:
            qty = int(request.form.get(f"qty_{item['id']}", item['quantity']))
            item['quantity'] = max(1, qty)
        session['cart'] = cart
        flash('Cart updated', 'success')
        return redirect(url_for('cart'))
    cart = session.get('cart', [])
    total = cart_total(cart)
    return render_template('cart.html', cart=cart, total=total)


@app.route('/remove_from_cart/<int:pid>')
def remove_from_cart(pid):
    cart = session.get('cart', [])
    cart = [item for item in cart if item['id'] != pid]
    session['cart'] = cart
    flash('Item removed from cart', 'success')
    return redirect(url_for('cart'))


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    cart = session.get('cart', [])
    if not cart:
        flash('Your cart is empty', 'error')
        return redirect(url_for('index'))
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        city = request.form.get('city')
        pincode = request.form.get('pincode')
        total = cart_total(cart)

        conn = get_db()
        est_dates = []
        for item in cart:
            pr = conn.execute('SELECT * FROM products WHERE id=?', (item['id'],)).fetchone()
            est_dates.append(calculate_estimated_date(pr))
        est_date = max(est_dates) if est_dates else (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')

        cur = conn.cursor()
        cur.execute('INSERT INTO orders (customer_name, email, phone, address, city, pincode, total_amount, payment_status, created_at, estimated_delivery_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (name, email, phone, address, city, pincode, total, 'pending', datetime.now().isoformat(), est_date))
        order_id = cur.lastrowid
        for item in cart:
            cur.execute('INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)',
                        (order_id, item['id'], item['quantity'], item['price']))

        # Create Razorpay order if configured
        rz_order_id = None
        if client:
            rz_order = client.order.create({
                'amount': int(total * 100),
                'currency': 'INR',
                'receipt': f'order_rcpt_{order_id}',
                'notes': {'local_order_id': str(order_id)}
            })
            rz_order_id = rz_order.get('id')
            cur.execute('UPDATE orders SET razorpay_order_id=? WHERE id=?', (rz_order_id, order_id))

        conn.commit(); conn.close()

        session['current_order_id'] = order_id
        return redirect(url_for('pay'))

    # Pre-fill user data if logged in
    user_data = {}
    if session.get('user_logged_in'):
        user_id = session.get('user_id')
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
        conn.close()
        if user:
            user_data = {
                'name': user['full_name'],
                'email': user['email'],
                'phone': user['phone'],
                'address': user['address'],
                'city': user['city'],
                'pincode': user['pincode']
            }
    
    return render_template('checkout.html', cart=cart, total=cart_total(cart), user_data=user_data)


@app.route('/pay', methods=['GET'])
def pay():
    order_id = session.get('current_order_id')
    if not order_id:
        flash('No order to pay for', 'error')
        return redirect(url_for('index'))
    conn = get_db()
    order = conn.execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone()
    conn.close()
    if not client or not RAZORPAY_KEY_ID:
        flash('Payment gateway not configured. Using mock screen.', 'error')
        return render_template('pay_mock.html', order=order)
    return render_template('pay.html', order=order, env_key_id=RAZORPAY_KEY_ID)


@app.route('/razorpay/callback', methods=['POST'])
def razorpay_callback():
    data = request.get_json(force=True)
    payment_id = data.get('razorpay_payment_id')
    order_id   = data.get('razorpay_order_id')
    signature  = data.get('razorpay_signature')
    if not (RAZORPAY_KEY_SECRET and payment_id and order_id and signature):
        return {'status':'missing-fields'}, 400

    body = f"{order_id}|{payment_id}"
    expected = hmac.new(RAZORPAY_KEY_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
    if hmac.compare_digest(expected, signature):
        conn = get_db()
        conn.execute("UPDATE orders SET payment_status='paid' WHERE razorpay_order_id=?", (order_id,))
        conn.commit(); conn.close()
        session.pop('cart', None)
        session.pop('current_order_id', None)
        return {'status':'ok'}
    return {'status':'invalid-signature'}, 400


@app.route('/order/<int:order_id>/success')
def order_success(order_id):
    conn = get_db()
    order = conn.execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone()
    items = conn.execute('SELECT oi.*, p.name FROM order_items oi JOIN products p ON oi.product_id=p.id WHERE order_id=?', (order_id,)).fetchall()
    conn.close()
    return render_template('order_success.html', order=order, items=items)

########################
# Webhooks (recommended)
########################

@app.route('/razorpay/webhook', methods=['POST'])
def razorpay_webhook():
    raw = request.get_data()
    provided = request.headers.get('X-Razorpay-Signature', '')
    secret = RAZORPAY_WEBHOOK_SECRET
    if not secret:
        return 'webhook-secret-not-set', 400
    expected = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, provided):
        return 'signature-mismatch', 400
    payload = request.get_json(force=True)
    event = payload.get('event')
    if event in ('payment.captured','order.paid'):
        try:
            rz_order_id = payload['payload']['order']['entity']['id']
            conn = get_db()
            conn.execute("UPDATE orders SET payment_status='paid' WHERE razorpay_order_id=?", (rz_order_id,))
            conn.commit(); conn.close()
        except Exception:
            pass
    return 'ok', 200

########################
# User Authentication Routes
########################

@app.route('/user/register', methods=['GET', 'POST'])
def user_register():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        
        # Validation
        if not email or not password or not full_name:
            flash('Email, password, and name are required', 'error')
            return redirect(url_for('user_register'))
        
        if password != password_confirm:
            flash('Passwords do not match', 'error')
            return redirect(url_for('user_register'))
        
        if len(password) < 6:
            flash('Password must be at least 6 characters', 'error')
            return redirect(url_for('user_register'))
        
        conn = get_db()
        existing = conn.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone()
        if existing:
            conn.close()
            flash('Email already registered', 'error')
            return redirect(url_for('user_register'))
        
        try:
            conn.execute('INSERT INTO users (email, password_hash, full_name, phone, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)',
                        (email, generate_password_hash(password), full_name, phone, datetime.now().isoformat(), datetime.now().isoformat()))
            conn.commit()
            conn.close()
            flash('Registration successful! Please log in.', 'success')
            # Set flag for first-time login
            session['first_time_login'] = True
            return redirect(url_for('user_login'))
        except Exception as e:
            conn.close()
            flash(f'Registration failed: {str(e)}', 'error')
            return redirect(url_for('user_register'))
    
    return render_template('user_register.html')


@app.route('/user/login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Email and password are required', 'error')
            return redirect(url_for('user_login'))
        
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session.permanent = True
            session['user_logged_in'] = True
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            session['user_name'] = user['full_name']
            
            # Check if this is first-time login after registration
            if session.get('first_time_login'):
                session.pop('first_time_login', None)
                flash(f'Welcome, {user["full_name"]}! Your account is ready.', 'success')
            else:
                flash(f'Welcome back, {user["full_name"]}!', 'success')
            return redirect(url_for('index'))
        
        flash('Invalid email or password', 'error')
        return redirect(url_for('user_login'))
    
    return render_template('user_login.html')


@app.route('/user/logout')
def user_logout():
    session.pop('user_logged_in', None)
    session.pop('user_id', None)
    session.pop('user_email', None)
    session.pop('user_name', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))


@app.route('/user/profile', methods=['GET', 'POST'])
def user_profile():
    if not session.get('user_logged_in'):
        flash('Please log in first', 'error')
        return redirect(url_for('user_login'))
    
    user_id = session.get('user_id')
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
    
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        city = request.form.get('city', '').strip()
        pincode = request.form.get('pincode', '').strip()
        
        conn.execute('UPDATE users SET full_name=?, phone=?, address=?, city=?, pincode=?, updated_at=? WHERE id=?',
                    (full_name, phone, address, city, pincode, datetime.now().isoformat(), user_id))
        conn.commit()
        
        # Update session
        session['user_name'] = full_name
        
        conn.close()
        flash('Profile updated successfully', 'success')
        return redirect(url_for('user_profile'))
    
    conn.close()
    return render_template('user_profile.html', user=user)


@app.route('/user/orders')
def user_orders():
    if not session.get('user_logged_in'):
        flash('Please log in first', 'error')
        return redirect(url_for('user_login'))
    
    email = session.get('user_email')
    conn = get_db()
    orders = conn.execute('SELECT * FROM orders WHERE email=? ORDER BY created_at DESC', (email,)).fetchall()
    conn.close()
    return render_template('user_orders.html', orders=orders)

########################
# Admin routes
########################

def is_admin():
    return session.get('admin_logged_in') is True


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        conn = get_db()
        admin = conn.execute('SELECT * FROM admin_users WHERE username=?', (username,)).fetchone()
        conn.close()
        if admin and check_password_hash(admin['password_hash'], password):
            session.permanent = True  # Make session permanent
            session['admin_logged_in'] = True
            session['admin_username'] = username  # Store username in session
            flash('Welcome, admin!', 'success')
            return redirect(url_for('admin_dashboard'))
        flash('Invalid credentials', 'error')
    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)  # Clear username from session
    flash('Logged out', 'success')
    return redirect(url_for('admin_login'))


@app.route('/admin')
def admin_dashboard():
    if not is_admin():
        return redirect(url_for('admin_login'))
    conn = get_db()
    stats = {
        'products': conn.execute('SELECT COUNT(*) as c FROM products').fetchone()['c'],
        'orders': conn.execute('SELECT COUNT(*) as c FROM orders').fetchone()['c'],
        'revenue': conn.execute("SELECT IFNULL(SUM(total_amount), 0) as s FROM orders WHERE payment_status='paid'").fetchone()['s'],
    }
    conn.close()
    return render_template('admin_dashboard.html', stats=stats)


@app.route('/admin/products')
def admin_products():
    if not is_admin():
        return redirect(url_for('admin_login'))
    conn = get_db()
    products = conn.execute('SELECT * FROM products ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('admin_products.html', products=products)


@app.route('/admin/product/new', methods=['GET', 'POST'])
def admin_product_new():
    if not is_admin():
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = float(request.form.get('price', '0'))
        stock = int(request.form.get('stock', '0'))
        est_days = request.form.get('estimated_delivery_days')
        est_date = request.form.get('estimated_delivery_date')
        
        # Handle image upload
        image_path = None
        if 'image' in request.files and request.files['image'].filename != '':
            file = request.files['image']
            # Create temporary product to get ID for filename
            conn = get_db()
            cursor = conn.execute('INSERT INTO products (name, description, price, stock, estimated_delivery_days, estimated_delivery_date) VALUES (?, ?, ?, ?, ?, ?)',
                         (name, description, price, stock, est_days if est_days else None, est_date if est_date else None))
            conn.commit()
            product_id = cursor.lastrowid
            conn.close()
            
            # Save image
            image_path = save_product_image(file, product_id)
            
            # Update product with image path
            if image_path:
                conn = get_db()
                conn.execute('UPDATE products SET image_path=? WHERE id=?', (image_path, product_id))
                conn.commit(); conn.close()
            
            flash('Product created', 'success')
            return redirect(url_for('admin_products'))
        else:
            conn = get_db()
            conn.execute('INSERT INTO products (name, description, price, stock, estimated_delivery_days, estimated_delivery_date) VALUES (?, ?, ?, ?, ?, ?)',
                         (name, description, price, stock, est_days if est_days else None, est_date if est_date else None))
            conn.commit(); conn.close()
            flash('Product created', 'success')
            return redirect(url_for('admin_products'))
    return render_template('admin_product_form.html', product=None)


@app.route('/admin/product/<int:pid>/edit', methods=['GET', 'POST'])
def admin_product_edit(pid):
    if not is_admin():
        return redirect(url_for('admin_login'))
    conn = get_db()
    product = conn.execute('SELECT * FROM products WHERE id=?', (pid,)).fetchone()
    if not product:
        conn.close()
        flash('Product not found', 'error')
        return redirect(url_for('admin_products'))
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = float(request.form.get('price', '0'))
        stock = int(request.form.get('stock', '0'))
        est_days = request.form.get('estimated_delivery_days')
        est_date = request.form.get('estimated_delivery_date')
        
        # Handle image upload
        image_path = product['image_path']
        if 'image' in request.files and request.files['image'].filename != '':
            file = request.files['image']
            new_image_path = save_product_image(file, pid)
            if new_image_path:
                # Delete old image if exists
                if image_path:
                    old_filepath = os.path.join('static', image_path)
                    if os.path.exists(old_filepath):
                        try:
                            os.remove(old_filepath)
                        except:
                            pass
                image_path = new_image_path
        
        conn.execute('UPDATE products SET name=?, description=?, price=?, stock=?, estimated_delivery_days=?, estimated_delivery_date=?, image_path=? WHERE id=?',
                     (name, description, price, stock, est_days if est_days else None, est_date if est_date else None, image_path, pid))
        conn.commit(); conn.close()
        flash('Product updated', 'success')
        return redirect(url_for('admin_products'))
    conn.close()
    return render_template('admin_product_form.html', product=product)


@app.route('/admin/product/<int:pid>/delete', methods=['POST'])
def admin_product_delete(pid):
    if not is_admin():
        return redirect(url_for('admin_login'))
    conn = get_db()
    conn.execute('DELETE FROM products WHERE id=?', (pid,))
    conn.commit(); conn.close()
    flash('Product deleted', 'success')
    return redirect(url_for('admin_products'))


@app.route('/admin/orders')
def admin_orders():
    if not is_admin():
        return redirect(url_for('admin_login'))
    conn = get_db()
    orders = conn.execute('SELECT * FROM orders ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('admin_orders.html', orders=orders)


@app.route('/admin/order/<int:oid>/status', methods=['POST'])
def admin_order_status(oid):
    if not is_admin():
        return redirect(url_for('admin_login'))
    status = request.form.get('status')
    est_date = request.form.get('estimated_delivery_date')
    conn = get_db()
    conn.execute('UPDATE orders SET payment_status=?, estimated_delivery_date=? WHERE id=?', (status, est_date, oid))
    conn.commit(); conn.close()
    flash('Order updated', 'success')
    return redirect(url_for('admin_orders'))


if __name__ == '__main__':
    app.run(debug=True)
