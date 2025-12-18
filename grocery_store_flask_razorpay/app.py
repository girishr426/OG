from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3, os, hmac, hashlib
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

# Optional: Razorpay SDK (install via pip)
try:
    import razorpay
except ImportError:
    razorpay = None

app = Flask(__name__)
app.secret_key = os.environ.get('APP_SECRET_KEY', 'change-this-secret-key')
DB_PATH = 'store.db'

RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET')
RAZORPAY_WEBHOOK_SECRET = os.environ.get('RAZORPAY_WEBHOOK_SECRET')

client = None
if razorpay and RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

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
            estimated_delivery_date TEXT
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
            ('Basmati Rice 5kg', 'Premium aged basmati rice', 649.0, 50, 2, None),
            ('Fresh Milk 1L', 'Pasteurized toned milk', 58.0, 100, 1, None),
            ('Organic Eggs (12)', 'Free-range organic eggs', 110.0, 80, 2, None),
            ('Tomatoes 1kg', 'Farm-fresh tomatoes', 35.0, 150, 1, None),
        ]
        cur.executemany('INSERT INTO products (name, description, price, stock, estimated_delivery_days, estimated_delivery_date) VALUES (?, ?, ?, ?, ?, ?)', sample)
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

    return render_template('checkout.html', cart=cart, total=cart_total(cart))


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
# Admin routes (unchanged)
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
            session['admin_logged_in'] = True
            flash('Welcome, admin!', 'success')
            return redirect(url_for('admin_dashboard'))
        flash('Invalid credentials', 'error')
    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
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
        conn.execute('UPDATE products SET name=?, description=?, price=?, stock=?, estimated_delivery_days=?, estimated_delivery_date=? WHERE id=?',
                     (name, description, price, stock, est_days if est_days else None, est_date if est_date else None, pid))
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
