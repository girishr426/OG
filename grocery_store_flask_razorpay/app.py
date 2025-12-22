from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3, os, hmac, hashlib
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image, ImageOps

# Load environment variables from .env files if available (without hard import)
import importlib.util, importlib
_dotenv_spec = importlib.util.find_spec("dotenv")
if _dotenv_spec is not None:
    _dotenv = importlib.import_module("dotenv")
    # Load root .env first, then override with data/.env if present
    _dotenv.load_dotenv()
    _dotenv.load_dotenv(dotenv_path=os.path.join('data', '.env'), override=True)

# Optional: Razorpay SDK (install via pip)
try:
    import razorpay
except ImportError:
    razorpay = None

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = os.environ.get('APP_SECRET_KEY', 'change-this-secret-key')
DB_PATH = 'store.db'

# Reusable SQL and message constants (avoid duplication)
SQL_SELECT_PRODUCT_BY_ID = 'SELECT * FROM products WHERE id=?'
SQL_SELECT_PRODUCTS_ORDERED = 'SELECT * FROM products ORDER BY id DESC'
SQL_SELECT_USER_BY_EMAIL = 'SELECT * FROM users WHERE email=?'
SQL_SELECT_USER_BY_ID = 'SELECT * FROM users WHERE id=?'
SQL_SELECT_ORDERS_BY_EMAIL = 'SELECT * FROM orders WHERE email=? ORDER BY created_at DESC'
MSG_PRODUCT_NOT_FOUND = 'Product not found'
SQL_SELECT_REGION_ID_NAME_ORDERED = 'SELECT id, name FROM regions ORDER BY name'
SQL_INSERT_PRODUCT_REGION = 'INSERT OR IGNORE INTO product_regions (product_id, region_id) VALUES (?, ?)'
SQL_DELETE_PRODUCT_REGIONS = 'DELETE FROM product_regions WHERE product_id=?'
VALID_PRODUCT_STATUSES = ['Upcoming Harvest', 'Harvest Complete', 'Final Product']

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
IMAGE_DEFAULT_SIZE = (800, 800)  # Default bounding box for uploaded images
IMAGE_JPEG_QUALITY = 85

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['MAX_CONTENT_LENGTH'] = MAX_IMAGE_SIZE


RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET')
RAZORPAY_WEBHOOK_SECRET = os.environ.get('RAZORPAY_WEBHOOK_SECRET')

client = None
if razorpay and RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# Optional HTTP client (requests) for external integrations
try:
    import requests  # type: ignore
except Exception:
    requests = None

# Site/meta settings and integrations
SITE_TITLE = os.environ.get('SITE_TITLE', 'Organic Gut Point')
SITE_DESCRIPTION = os.environ.get('SITE_DESCRIPTION', 'Organic groceries delivered fresh to your door.')
SITE_BASE_URL = os.environ.get('SITE_BASE_URL', '')  # e.g., https://organicgut.example.com
SITE_ANNOUNCEMENT = os.environ.get('SITE_ANNOUNCEMENT', '')

# Brevo (Sendinblue) optional integration
BREVO_API_KEY = os.environ.get('BREVO_API_KEY')
BREVO_LIST_ID = os.environ.get('BREVO_LIST_ID')  # integer string
WHATSAPP_NUMBER = os.environ.get('WHATSAPP_NUMBER')  # e.g., +919876543210


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_product_image(file, product_id):
    """Save and optimize product image: auto-fit to default size, correct orientation, and compress.
    Always stores as JPEG to reduce size.
    """
    if not file or file.filename == '':
        return None
    
    if not allowed_file(file.filename):
        flash('Invalid file type. Allowed: JPG, PNG, GIF', 'error')
        return None
    
    try:
        # Save with secure filename
        filename = secure_filename(f"product_{product_id}_{int(datetime.now().timestamp())}.jpg")
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        # Open image and normalize
        img = Image.open(file)
        # Correct orientation from EXIF if present
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass
        # Convert to RGB for consistent JPEG output
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # Fit into bounding box without upscaling
        img = ImageOps.contain(img, IMAGE_DEFAULT_SIZE, Image.LANCZOS)

        # Save optimized JPEG
        img.save(filepath, 'JPEG', quality=IMAGE_JPEG_QUALITY, optimize=True, progressive=True)

        return f'product_images/{filename}'
    except Exception as e:
        flash(f'Error uploading image: {str(e)}', 'error')
        return None


def replace_product_image(pid, current_image_path, uploaded_file):
    """Save a new image for a product and remove the previous one if present.
    Returns the final image path to store for the product.
    """
    if not uploaded_file or uploaded_file.filename == '':
        return current_image_path
    new_image_path = save_product_image(uploaded_file, pid)
    if new_image_path:
        if current_image_path:
            old_filepath = os.path.join('static', current_image_path)
            if os.path.exists(old_filepath):
                try:
                    os.remove(old_filepath)
                except OSError:
                    # Ignore file removal errors
                    pass
        return new_image_path
    return current_image_path


def save_product_catalog_images(product_id, image_files):
    """Save multiple images for a product catalog/gallery.
    Returns list of saved image paths.
    """
    if not image_files:
        return []
    
    saved_images = []
    for idx, file in enumerate(image_files):
        if file and file.filename != '':
            image_path = save_product_image(file, product_id)
            if image_path:
                saved_images.append({
                    'path': image_path,
                    'order': idx,
                    'is_primary': 1 if idx == 0 else 0
                })
    return saved_images


def add_product_images_to_db(product_id, image_data_list):
    """Add multiple images to product_images table.
    image_data_list: List of dicts with 'path', 'order', 'is_primary' keys
    """
    conn = get_db()
    try:
        for img_data in image_data_list:
            conn.execute(
                'INSERT INTO product_images (product_id, image_path, display_order, is_primary, created_at) VALUES (?, ?, ?, ?, ?)',
                (product_id, img_data['path'], img_data['order'], img_data['is_primary'], datetime.now().isoformat())
            )
        conn.commit()
    finally:
        conn.close()


def get_product_images(product_id):
    """Fetch all images for a product, ordered by display_order."""
    conn = get_db()
    images = conn.execute(
        'SELECT id, image_path, display_order, is_primary FROM product_images WHERE product_id=? ORDER BY display_order, is_primary DESC',
        (product_id,)
    ).fetchall()
    conn.close()
    return images


# ==========================
# Reviews utilities
# ==========================

def user_verified_purchase(email: str, product_id: int) -> bool:
    """Return True if the given email has at least one PAID order containing the product."""
    if not email:
        return False
    conn = get_db()
    row = conn.execute(
        """
        SELECT COUNT(*) as c
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.id
        WHERE o.email = ? AND o.payment_status = 'paid' AND oi.product_id = ?
        """,
        (email, product_id)
    ).fetchone()
    conn.close()
    return (row['c'] or 0) > 0


def compute_review_stats(product_id: int):
    """Compute average rating, total count, and per-star breakdown for approved reviews."""
    conn = get_db()
    stats = {'avg_rating': 0.0, 'total': 0, 'breakdown': {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}}
    rows = conn.execute(
        'SELECT rating, COUNT(*) as c FROM product_reviews WHERE product_id=? AND is_approved=1 GROUP BY rating',
        (product_id,)
    ).fetchall()
    total = 0
    ssum = 0
    for r in rows:
        rating = int(r['rating'])
        cnt = int(r['c'])
        if rating in stats['breakdown']:
            stats['breakdown'][rating] = cnt
        total += cnt
        ssum += rating * cnt
    stats['total'] = total
    stats['avg_rating'] = round((ssum / total) if total else 0.0, 1)
    conn.close()
    return stats


def fetch_product_reviews(product_id: int, sort: str = 'helpful', limit: int = 10, offset: int = 0):
    """Fetch approved reviews with user display name. sort in ['helpful','recent','rating_high','rating_low']"""
    order_clause = 'pr.helpful_count DESC, pr.created_at DESC'
    if sort == 'recent':
        order_clause = 'pr.created_at DESC'
    elif sort == 'rating_high':
        order_clause = 'pr.rating DESC, pr.created_at DESC'
    elif sort == 'rating_low':
        order_clause = 'pr.rating ASC, pr.created_at DESC'

    conn = get_db()
    reviews = conn.execute(
        f'''SELECT pr.*, u.full_name as user_name
            FROM product_reviews pr
            LEFT JOIN users u ON u.id = pr.user_id
            WHERE pr.product_id=? AND pr.is_approved=1
            ORDER BY {order_clause}
            LIMIT ? OFFSET ?''',
        (product_id, limit, offset)
    ).fetchall()
    conn.close()
    return reviews


def compute_review_stats_bulk(product_ids: list[int]):
    """Return mapping product_id -> {avg_rating: float, total: int} for approved reviews in a single query."""
    result: dict[int, dict] = {}
    if not product_ids:
        return result
    # Build placeholders for SQLite IN clause
    placeholders = ",".join(["?"] * len(product_ids))
    conn = get_db()
    rows = conn.execute(
        f'''SELECT product_id, AVG(rating) as avg_rating, COUNT(*) as total
            FROM product_reviews
            WHERE is_approved=1 AND product_id IN ({placeholders})
            GROUP BY product_id''',
        tuple(product_ids)
    ).fetchall()
    conn.close()
    for r in rows:
        pid = int(r['product_id'])
        avg_rating = float(r['avg_rating']) if r['avg_rating'] is not None else 0.0
        total = int(r['total']) if r['total'] is not None else 0
        result[pid] = {'avg_rating': round(avg_rating, 1), 'total': total}
    return result


def delete_product_image(image_id):
    """Delete a single image from product_images table and from filesystem."""
    conn = get_db()
    image_row = conn.execute('SELECT image_path FROM product_images WHERE id=?', (image_id,)).fetchone()
    
    if image_row:
        image_path = image_row['image_path']
        # Delete from database
        conn.execute('DELETE FROM product_images WHERE id=?', (image_id,))
        conn.commit()
        conn.close()
        
        # Delete from filesystem
        filepath = os.path.join('static', image_path)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except OSError:
                pass
        return True
    conn.close()
    return False


########################
# Database utilities
########################

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database with schema and run migrations if needed."""
    conn = get_db()
    cur = conn.cursor()
    
    # Create schema_version table first (for tracking applied migrations)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS schema_version (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version INTEGER NOT NULL UNIQUE,
            description TEXT,
            applied_at TEXT NOT NULL,
            status TEXT DEFAULT 'applied'
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            mrp REAL,
            stock INTEGER DEFAULT 0,
            estimated_delivery_days INTEGER,
            estimated_delivery_date TEXT,
            image_path TEXT,
            is_homepage INTEGER DEFAULT 0,
            product_status TEXT DEFAULT 'Final Product',
            category TEXT DEFAULT 'Products'
        )
    ''')
    # Backfill migration: add mrp column if missing in existing DBs
    try:
        cols = cur.execute("PRAGMA table_info(products)").fetchall()
        col_names = {c[1] for c in cols}
        if 'mrp' not in col_names:
            cur.execute('ALTER TABLE products ADD COLUMN mrp REAL')
            conn.commit()
        if 'category' not in col_names:
            cur.execute('ALTER TABLE products ADD COLUMN category TEXT DEFAULT "Products"')
            conn.commit()
        if 'size' not in col_names:
            cur.execute('ALTER TABLE products ADD COLUMN size TEXT DEFAULT "Standard"')
            conn.commit()
    except Exception:
        pass
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
    # Regions of Karnataka
    cur.execute('''
        CREATE TABLE IF NOT EXISTS regions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            state TEXT NOT NULL
        )
    ''')
    # Product to Region availability mapping (many-to-many)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS product_regions (
            product_id INTEGER NOT NULL,
            region_id INTEGER NOT NULL,
            UNIQUE(product_id, region_id),
            FOREIGN KEY(product_id) REFERENCES products(id),
            FOREIGN KEY(region_id) REFERENCES regions(id)
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS contact_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            subject TEXT,
            message TEXT NOT NULL,
            created_at TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS newsletter_subscribers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            created_at TEXT
        )
    ''')
    # Product catalog images (multiple images per product for gallery display)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS product_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            image_path TEXT NOT NULL,
            display_order INTEGER DEFAULT 0,
            is_primary INTEGER DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    ''')
    # Catalog region images (left and right body regions)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS catalog_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            region TEXT NOT NULL,
            position INTEGER NOT NULL,
            image_path TEXT NOT NULL,
            alt_text TEXT,
            created_at TEXT,
            updated_at TEXT,
            UNIQUE(region, position)
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT
        )
    ''')
    # Product reviews and helpful votes
    cur.execute('''
        CREATE TABLE IF NOT EXISTS product_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            user_id INTEGER,
            rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
            title TEXT,
            body TEXT NOT NULL,
            verified_purchase INTEGER DEFAULT 0,
            helpful_count INTEGER DEFAULT 0,
            is_approved INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS review_votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            vote INTEGER NOT NULL DEFAULT 1,
            created_at TEXT,
            UNIQUE(review_id, user_id),
            FOREIGN KEY(review_id) REFERENCES product_reviews(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    # Community features: Posts, Comments, Likes
    cur.execute('''
        CREATE TABLE IF NOT EXISTS community_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            category TEXT DEFAULT 'General',
            likes_count INTEGER DEFAULT 0,
            comments_count INTEGER DEFAULT 0,
            is_featured INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS community_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            body TEXT NOT NULL,
            likes_count INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY(post_id) REFERENCES community_posts(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS community_likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            comment_id INTEGER,
            user_id INTEGER NOT NULL,
            created_at TEXT,
            UNIQUE(post_id, user_id),
            UNIQUE(comment_id, user_id),
            FOREIGN KEY(post_id) REFERENCES community_posts(id) ON DELETE CASCADE,
            FOREIGN KEY(comment_id) REFERENCES community_comments(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    # Seed default admin if not exists
    cur.execute('SELECT COUNT(*) as c FROM admin_users')
    if cur.fetchone()['c'] == 0:
        # Use env var for default admin password, otherwise generate a secure one and print it once.
        default_admin_password = os.environ.get('ADMIN_DEFAULT_PASSWORD')
        if not default_admin_password:
            # Generate a random password for safety in case env is not set
            default_admin_password = os.urandom(12).hex()
            print("[INIT] Generated admin password (set ADMIN_DEFAULT_PASSWORD to override):", default_admin_password)
        cur.execute('INSERT INTO admin_users (username, password_hash) VALUES (?, ?)', (
            'admin', generate_password_hash(default_admin_password)
        ))
    
    conn.commit()
    # Seed Karnataka regions if none
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) as c FROM regions')
    if cur.fetchone()['c'] == 0:
        karnataka_regions = [
            ('Bengaluru Urban','Karnataka'), ('Bengaluru Rural','Karnataka'), ('Mysuru','Karnataka'),
            ('Mandya','Karnataka'), ('Hassan','Karnataka'), ('Chikkamagaluru','Karnataka'), ('Kodagu','Karnataka'),
            ('Udupi','Karnataka'), ('Dakshina Kannada','Karnataka'), ('Shivamogga','Karnataka'), ('Chitradurga','Karnataka'),
            ('Davanagere','Karnataka'), ('Ballari','Karnataka'), ('Vijayanagara','Karnataka'), ('Koppal','Karnataka'),
            ('Raichur','Karnataka'), ('Gadag','Karnataka'), ('Haveri','Karnataka'), ('Dharwad','Karnataka'),
            ('Uttara Kannada','Karnataka'), ('Belagavi','Karnataka'), ('Vijayapura','Karnataka'), ('Bagalkot','Karnataka'),
            ('Kalaburagi','Karnataka'), ('Yadgir','Karnataka'), ('Bidar','Karnataka'), ('Tumakuru','Karnataka'),
            ('Ramanagara','Karnataka'), ('Chikkaballapura','Karnataka'), ('Kolar','Karnataka')
        ]
        cur.executemany('INSERT INTO regions (name, state) VALUES (?, ?)', karnataka_regions)
        conn.commit()
    
    # Track applied migrations (v1 = initial setup with schema)
    cur.execute('SELECT MAX(version) as max_v FROM schema_version')
    result = cur.fetchone()
    max_version = result['max_v'] if result['max_v'] else 0
    
    # v1: Initial schema (all tables created above)
    if max_version < 1:
        try:
            cur.execute('INSERT INTO schema_version (version, description, applied_at, status) VALUES (?, ?, ?, ?)',
                       (1, 'Initial schema with all tables and columns', datetime.now().isoformat(), 'applied'))
            conn.commit()
        except Exception:
            pass
    
    # v2: MRP column (already added above in backfill, but track it)
    if max_version < 2:
        try:
            cols = cur.execute("PRAGMA table_info(products)").fetchall()
            col_names = {c[1] for c in cols}
            if 'mrp' not in col_names:
                cur.execute('ALTER TABLE products ADD COLUMN mrp REAL')
            cur.execute('INSERT INTO schema_version (version, description, applied_at, status) VALUES (?, ?, ?, ?)',
                       (2, 'Added MRP column to products table', datetime.now().isoformat(), 'applied'))
            conn.commit()
        except Exception:
            pass
    
    # v3: Size column
    if max_version < 3:
        try:
            cols = cur.execute("PRAGMA table_info(products)").fetchall()
            col_names = {c[1] for c in cols}
            if 'size' not in col_names:
                cur.execute('ALTER TABLE products ADD COLUMN size TEXT DEFAULT "Standard"')
            cur.execute('INSERT INTO schema_version (version, description, applied_at, status) VALUES (?, ?, ?, ?)',
                       (3, 'Added size column to products table', datetime.now().isoformat(), 'applied'))
            conn.commit()
        except Exception:
            pass
    
    # v4: Catalog images table
    if max_version < 4:
        try:
            cur.execute('INSERT INTO schema_version (version, description, applied_at, status) VALUES (?, ?, ?, ?)',
                       (4, 'Created catalog_images table for hero carousel', datetime.now().isoformat(), 'applied'))
            conn.commit()
        except Exception:
            pass
    
    # v5: Product images table
    if max_version < 5:
        try:
            cur.execute('INSERT INTO schema_version (version, description, applied_at, status) VALUES (?, ?, ?, ?)',
                       (5, 'Created product_images table for product gallery', datetime.now().isoformat(), 'applied'))
            conn.commit()
        except Exception:
            pass
    
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
# Template context
########################

@app.context_processor
def inject_site_meta():
    # Fetch regions for header selector; safe if DB not initialized yet
    regions = []
    try:
        conn = get_db()
        regions = conn.execute(SQL_SELECT_REGION_ID_NAME_ORDERED).fetchall()
        conn.close()
    except Exception:
        pass
    # Current selected region
    current_region_id = session.get('region_id')
    current_region_name = None
    try:
        if current_region_id:
            conn = get_db()
            r = conn.execute('SELECT name FROM regions WHERE id=?', (current_region_id,)).fetchone()
            conn.close()
            if r:
                current_region_name = r['name']
    except Exception:
        pass
    # Current selected product status
    current_product_status = session.get('product_status')
    
    # Fetch catalog images
    catalog_images = {}
    try:
        conn = get_db()
        images = conn.execute('SELECT region, position, image_path, alt_text FROM catalog_images ORDER BY region, position').fetchall()
        conn.close()
        for img in images:
            region = img['region']
            if region not in catalog_images:
                catalog_images[region] = []
            catalog_images[region].append({
                'position': img['position'],
                'path': img['image_path'],
                'alt': img['alt_text']
            })
    except Exception:
        pass
    
    return {
        'site_meta': {
            'title': SITE_TITLE,
            'description': SITE_DESCRIPTION,
            'base_url': SITE_BASE_URL,
        },
        'site_announcement': SITE_ANNOUNCEMENT,
        'regions': regions,
        'current_region_id': current_region_id,
        'current_region_name': current_region_name,
        'current_product_status': current_product_status,
        'whatsapp_number': WHATSAPP_NUMBER,
        'catalog_images': catalog_images,
    }

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

def set_product_regions(product_id: int, region_ids: list):
    """Replace product's region mappings with provided list of region ids."""
    try:
        conn = get_db()
        # Remove existing
        conn.execute(SQL_DELETE_PRODUCT_REGIONS, (product_id,))
        # Add new
        for r in (region_ids or []):
            try:
                conn.execute(SQL_INSERT_PRODUCT_REGION, (product_id, int(r)))
            except Exception:
                pass
        conn.commit(); conn.close()
    except Exception:
        pass

########################
# Public routes
########################

@app.route('/')
def index():
    conn = get_db()
    region_id = session.get('region_id')
    product_status = session.get('product_status')
    is_homepage = False
    page_title = 'Products'
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'new')
    if page < 1:
        page = 1
    
    PRODUCTS_PER_PAGE = 12
    
    if region_id == 'all':
        # "All Regions" selected: show all products EXCEPT special categories
        all_products = conn.execute('SELECT * FROM products WHERE category = "Products" ORDER BY id DESC').fetchall()
        page_title = 'All Products'
    elif region_id:
        # Show products available in selected region OR globally available (no mappings) - EXCEPT special categories
        all_products = conn.execute('''
            SELECT p.* FROM products p
            WHERE p.category = "Products"
              AND (NOT EXISTS (SELECT 1 FROM product_regions pr WHERE pr.product_id = p.id)
               OR EXISTS (SELECT 1 FROM product_regions pr WHERE pr.product_id = p.id AND pr.region_id = ?))
            ORDER BY p.id DESC
        ''', (region_id,)).fetchall()
    else:
        # No region selected: show homepage products if sorting is 'new', otherwise show all Products
        if sort == 'new':
            homepage_products = conn.execute('SELECT p.* FROM products p WHERE p.is_homepage = 1 AND p.category = "Products" ORDER BY p.id DESC').fetchall()
            if homepage_products:
                all_products = homepage_products
                is_homepage = True
                page_title = 'New Products'
            else:
                # Fallback: show Products category items only
                all_products = conn.execute('SELECT * FROM products WHERE category = "Products" ORDER BY id DESC').fetchall()
        else:
            # When sorting by price or name, show ALL products
            all_products = conn.execute('SELECT * FROM products WHERE category = "Products" ORDER BY id DESC').fetchall()
            page_title = 'Products'
    
    # Filter by product status if selected (but not if 'all' is selected)
    if product_status and product_status != 'all':
        all_products = [p for p in all_products if p['product_status'] == product_status]
    # Sorting like marketplace UX
    if sort == 'price_low':
        all_products = sorted(all_products, key=lambda p: (p['price'] or 0))
    elif sort == 'price_high':
        all_products = sorted(all_products, key=lambda p: (p['price'] or 0), reverse=True)
    elif sort == 'name_az':
        all_products = sorted(all_products, key=lambda p: (p['name'] or '').lower())
    # else 'new' keeps default ordering

    conn.close()
    
    # Pagination logic
    total_products = len(all_products)
    total_pages = (total_products + PRODUCTS_PER_PAGE - 1) // PRODUCTS_PER_PAGE
    
    if page > total_pages and total_pages > 0:
        page = total_pages
    
    start_idx = (page - 1) * PRODUCTS_PER_PAGE
    end_idx = start_idx + PRODUCTS_PER_PAGE
    products = all_products[start_idx:end_idx]
    # Bulk review stats for visible products (for star display on cards)
    review_stats_map = compute_review_stats_bulk([p['id'] for p in products])
    
    # Mark first 4 products as "new"
    new_product_ids = {p['id'] for p in all_products[:4]}
    
    # Get all products grouped by category for quick reference section
    conn = get_db()
    all_categories_products = {}
    categories_info = [
        ('Products', '🌾 Organic Products'),
        ('gutcare', '🌿 Gut Care'),
        ('corporate', '🏢 Corporate'),
        ('gifts', '🎁 Gifts')
    ]
    for category_key, category_label in categories_info:
        products_in_cat = conn.execute(
            'SELECT id, name, price, image_path FROM products WHERE category = ? ORDER BY id DESC LIMIT 8',
            (category_key,)
        ).fetchall()
        if products_in_cat:
            all_categories_products[category_key] = {
                'label': category_label,
                'products': products_in_cat
            }
    
    # Fetch Gut Care products for carousel (only when viewing newest products on homepage)
    gutcare_carousel_products = []
    if is_homepage and sort == 'new':
        gutcare_carousel_products = conn.execute(
            'SELECT id, name, price, image_path FROM products WHERE LOWER(category) = ? ORDER BY id DESC LIMIT 12',
            ('gutcare',)
        ).fetchall()
    
    conn.close()
    
    return render_template('index.html', 
                         products=products, 
                         new_product_ids=new_product_ids, 
                         title=page_title, 
                         is_homepage=is_homepage,
                         current_page=page,
                         total_pages=total_pages,
                         total_products=total_products,
                         review_stats_map=review_stats_map,
                         sort=sort,
                         all_categories_products=all_categories_products,
                         gutcare_carousel_products=gutcare_carousel_products)

@app.route('/category/<category>')
def category_view(category):
    """View products by category: gutcare, corporate, gifts"""
    conn = get_db()
    category_lower = category.lower()
    
    # Validate category
    valid_categories = ['gutcare', 'corporate', 'gifts']
    if category_lower not in valid_categories:
        return redirect(url_for('index'))
    
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'new')
    if page < 1:
        page = 1
    
    PRODUCTS_PER_PAGE = 12
    
    # Get products for this category
    all_products = conn.execute(
        'SELECT * FROM products WHERE LOWER(category) = ? ORDER BY id DESC',
        (category_lower,)
    ).fetchall()
    
    # Apply sorting
    if sort == 'price_low':
        all_products = sorted(all_products, key=lambda p: (p['price'] or 0))
    elif sort == 'price_high':
        all_products = sorted(all_products, key=lambda p: (p['price'] or 0), reverse=True)
    elif sort == 'name_az':
        all_products = sorted(all_products, key=lambda p: (p['name'] or '').lower())
    
    conn.close()
    
    # Pagination
    total_products = len(all_products)
    total_pages = (total_products + PRODUCTS_PER_PAGE - 1) // PRODUCTS_PER_PAGE
    start_idx = (page - 1) * PRODUCTS_PER_PAGE
    end_idx = start_idx + PRODUCTS_PER_PAGE
    products = all_products[start_idx:end_idx]
    
    # Mark first 4 as "new"
    new_product_ids = {p['id'] for p in all_products[:4]}
    
    # Category display names
    category_titles = {
        'gutcare': '🌿 Gut Care & Wellness Products',
        'corporate': '🏢 Corporate Gifting & Bulk Orders',
        'gifts': '🎁 Gift Hampers & Special Collections'
    }
    
    return render_template('index.html',
                         products=products,
                         new_product_ids=new_product_ids,
                         title=category_titles.get(category_lower, category),
                         is_homepage=False,
                         current_page=page,
                         total_pages=total_pages,
                         total_products=total_products,
                         review_stats_map={},
                         sort=sort)

@app.get('/customer-care/shipping')
def customer_shipping():
    return render_template('customer_shipping.html')

@app.get('/customer-care/returns')
def customer_returns():
    return render_template('customer_returns.html')

# ==========================
# COMMUNITY ROUTES
# ==========================

@app.route('/community')
def community_home():
    """View all community posts with pagination and categories"""
    if not session.get('user_logged_in') and not session.get('admin_logged_in'):
        flash('Please log in to access the community', 'info')
        return redirect(url_for('user_login'))
    
    page = request.args.get('page', 1, type=int)
    category_filter = request.args.get('category', 'All')
    if page < 1:
        page = 1
    
    POSTS_PER_PAGE = 10
    
    conn = get_db()
    
    # Build query
    where_clause = ''
    params = []
    if category_filter and category_filter != 'All':
        where_clause = 'WHERE category = ?'
        params.append(category_filter)
    
    # Get total count
    count_query = f'SELECT COUNT(*) as c FROM community_posts {where_clause}'
    total_posts = conn.execute(count_query, params).fetchone()['c']
    
    # Get paginated posts
    offset = (page - 1) * POSTS_PER_PAGE
    query = f'''
        SELECT cp.*, u.full_name as author_name 
        FROM community_posts cp
        JOIN users u ON cp.user_id = u.id
        {where_clause}
        ORDER BY cp.is_featured DESC, cp.created_at DESC
        LIMIT ? OFFSET ?
    '''
    params.extend([POSTS_PER_PAGE, offset])
    
    posts = conn.execute(query, params).fetchall()
    
    # Get all categories for filter
    categories_result = conn.execute(
        'SELECT DISTINCT category FROM community_posts ORDER BY category'
    ).fetchall()
    categories = ['All'] + [c['category'] for c in categories_result]
    
    conn.close()
    
    total_pages = (total_posts + POSTS_PER_PAGE - 1) // POSTS_PER_PAGE
    
    return render_template('community_home.html',
                         posts=posts,
                         categories=categories,
                         current_category=category_filter,
                         current_page=page,
                         total_pages=total_pages,
                         total_posts=total_posts)

@app.route('/community/post/<int:post_id>')
def community_post(post_id):
    """View single community post with comments"""
    if not session.get('user_logged_in') and not session.get('admin_logged_in'):
        flash('Please log in to access the community', 'info')
        return redirect(url_for('user_login'))
    
    conn = get_db()
    
    # Get post
    post = conn.execute('''
        SELECT cp.*, u.full_name as author_name, u.id as author_id
        FROM community_posts cp
        JOIN users u ON cp.user_id = u.id
        WHERE cp.id = ?
    ''', (post_id,)).fetchone()
    
    if not post:
        flash('Post not found', 'error')
        conn.close()
        return redirect(url_for('community_home'))
    
    # Get comments with user info
    comments = conn.execute('''
        SELECT cc.*, u.full_name as author_name
        FROM community_comments cc
        JOIN users u ON cc.user_id = u.id
        WHERE cc.post_id = ?
        ORDER BY cc.created_at DESC
    ''', (post_id,)).fetchall()
    
    # Check if current user liked the post
    user_id = session.get('user_id')
    user_liked_post = False
    if user_id:
        liked = conn.execute(
            'SELECT 1 FROM community_likes WHERE post_id = ? AND user_id = ?',
            (post_id, user_id)
        ).fetchone()
        user_liked_post = liked is not None
    
    conn.close()
    
    return render_template('community_post.html',
                         post=post,
                         comments=comments,
                         user_liked_post=user_liked_post)

@app.route('/community/post/new', methods=['GET', 'POST'])
def create_community_post():
    """Create new community post"""
    if not session.get('user_logged_in') and not session.get('admin_logged_in'):
        flash('Please log in to create a post', 'info')
        return redirect(url_for('user_login'))
    
    if request.method == 'POST':
        title = (request.form.get('title') or '').strip()
        body = (request.form.get('body') or '').strip()
        category = (request.form.get('category') or 'General').strip()
        
        if not title or not body:
            flash('Title and body are required', 'error')
            return render_template('community_post_form.html')
        
        if len(title) > 200:
            flash('Title must be less than 200 characters', 'error')
            return render_template('community_post_form.html', title=title, body=body, category=category)
        
        conn = get_db()
        user_id = session.get('user_id')
        
        try:
            conn.execute('''
                INSERT INTO community_posts (user_id, title, body, category, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, title, body, category, datetime.now().isoformat(), datetime.now().isoformat()))
            conn.commit()
            
            post_id = conn.execute('SELECT last_insert_rowid() as id').fetchone()['id']
            conn.close()
            
            flash('Post created successfully!', 'success')
            return redirect(url_for('community_post', post_id=post_id))
        except Exception as e:
            conn.close()
            flash(f'Error creating post: {str(e)}', 'error')
            return render_template('community_post_form.html', title=title, body=body, category=category)
    
    return render_template('community_post_form.html')

@app.route('/community/post/<int:post_id>/comment', methods=['POST'])
def add_community_comment(post_id):
    """Add comment to community post"""
    if not session.get('user_logged_in') and not session.get('admin_logged_in'):
        flash('Please log in to comment', 'info')
        return redirect(url_for('user_login'))
    
    body = (request.form.get('body') or '').strip()
    
    if not body:
        flash('Comment cannot be empty', 'error')
        return redirect(url_for('community_post', post_id=post_id))
    
    if len(body) > 1000:
        flash('Comment must be less than 1000 characters', 'error')
        return redirect(url_for('community_post', post_id=post_id))
    
    conn = get_db()
    user_id = session.get('user_id')
    
    try:
        # Insert comment
        conn.execute('''
            INSERT INTO community_comments (post_id, user_id, body, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (post_id, user_id, body, datetime.now().isoformat(), datetime.now().isoformat()))
        
        # Update post comment count
        conn.execute('''
            UPDATE community_posts 
            SET comments_count = (SELECT COUNT(*) FROM community_comments WHERE post_id = ?)
            WHERE id = ?
        ''', (post_id, post_id))
        
        conn.commit()
        conn.close()
        
        flash('Comment added successfully!', 'success')
        return redirect(url_for('community_post', post_id=post_id))
    except Exception as e:
        conn.close()
        flash(f'Error adding comment: {str(e)}', 'error')
        return redirect(url_for('community_post', post_id=post_id))

@app.route('/community/post/<int:post_id>/like', methods=['POST'])
def like_community_post(post_id):
    """Like/unlike a community post"""
    if not session.get('user_logged_in') and not session.get('admin_logged_in'):
        return {'success': False, 'message': 'Please log in'}, 401
    
    user_id = session.get('user_id')
    conn = get_db()
    
    # Check if already liked
    liked = conn.execute(
        'SELECT id FROM community_likes WHERE post_id = ? AND user_id = ?',
        (post_id, user_id)
    ).fetchone()
    
    try:
        if liked:
            # Unlike
            conn.execute('DELETE FROM community_likes WHERE post_id = ? AND user_id = ?', 
                        (post_id, user_id))
            liked_count_change = -1
        else:
            # Like
            conn.execute('''
                INSERT INTO community_likes (post_id, user_id, created_at)
                VALUES (?, ?, ?)
            ''', (post_id, user_id, datetime.now().isoformat()))
            liked_count_change = 1
        
        # Update post likes count
        conn.execute('''
            UPDATE community_posts 
            SET likes_count = (SELECT COUNT(*) FROM community_likes WHERE post_id = ?)
            WHERE id = ?
        ''', (post_id, post_id))
        
        conn.commit()
        
        # Get updated count
        new_count = conn.execute(
            'SELECT likes_count FROM community_posts WHERE id = ?',
            (post_id,)
        ).fetchone()['likes_count']
        
        conn.close()
        return {'success': True, 'liked': not liked, 'likes_count': new_count}
    except Exception as e:
        conn.close()
        return {'success': False, 'message': str(e)}, 500

@app.route('/community/comment/<int:comment_id>/like', methods=['POST'])
def like_community_comment(comment_id):
    """Like/unlike a community comment"""
    if not session.get('user_logged_in') and not session.get('admin_logged_in'):
        return {'success': False, 'message': 'Please log in'}, 401
    
    user_id = session.get('user_id')
    conn = get_db()
    
    # Check if already liked
    liked = conn.execute(
        'SELECT id FROM community_likes WHERE comment_id = ? AND user_id = ?',
        (comment_id, user_id)
    ).fetchone()
    
    try:
        if liked:
            # Unlike
            conn.execute('DELETE FROM community_likes WHERE comment_id = ? AND user_id = ?',
                        (comment_id, user_id))
        else:
            # Like
            conn.execute('''
                INSERT INTO community_likes (comment_id, user_id, created_at)
                VALUES (?, ?, ?)
            ''', (comment_id, user_id, datetime.now().isoformat()))
        
        # Update comment likes count
        conn.execute('''
            UPDATE community_comments
            SET likes_count = (SELECT COUNT(*) FROM community_likes WHERE comment_id = ?)
            WHERE id = ?
        ''', (comment_id, comment_id))
        
        conn.commit()
        
        # Get updated count
        new_count = conn.execute(
            'SELECT likes_count FROM community_comments WHERE id = ?',
            (comment_id,)
        ).fetchone()['likes_count']
        
        conn.close()
        return {'success': True, 'liked': not liked, 'likes_count': new_count}
    except Exception as e:
        conn.close()
        return {'success': False, 'message': str(e)}, 500

@app.route('/customer-care/contact', methods=['GET', 'POST'])
def customer_contact():
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        subject = (request.form.get('subject') or '').strip()
        message = (request.form.get('message') or '').strip()
        if not name or not email or not message or '@' not in email:
            flash('Please fill in your name, a valid email, and a message.', 'error')
            return redirect(url_for('customer_contact'))
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute('INSERT INTO contact_messages (name, email, subject, message, created_at) VALUES (?, ?, ?, ?, ?)',
                        (name, email, subject, message, datetime.now().isoformat()))
            conn.commit(); conn.close()
            flash('Thanks! We received your message and will get back to you soon.', 'success')
            return redirect(url_for('customer_contact'))
        except Exception:
            flash('Sorry, we could not submit your message right now.', 'error')
            return redirect(url_for('customer_contact'))
    return render_template('customer_contact.html')


@app.get('/search')
def search():
    q = (request.args.get('q') or '').strip()
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'new')
    if page < 1:
        page = 1
    
    conn = get_db()
    region_id = session.get('region_id')
    product_status = session.get('product_status')
    
    # If search is empty, show message and redirect to home
    if not q:
        flash('Please enter a search term to search for products', 'info')
        conn.close()
        return redirect(url_for('index'))
    
    PRODUCTS_PER_PAGE = 12
    
    # User searched for products with a non-empty query - EXCLUDE special categories
    like = f"%{q}%"
    if region_id == 'all':
        # "All Regions" selected + Search term: Show all matching products from Products category only
        all_products = conn.execute('SELECT * FROM products WHERE (name LIKE ? OR description LIKE ?) AND category = "Products" ORDER BY id DESC', (like, like)).fetchall()
    elif region_id:
        # Specific region selected + Search term: Show matching products from Products category only
        all_products = conn.execute('''
            SELECT p.* FROM products p
            WHERE p.category = "Products"
              AND (p.name LIKE ? OR p.description LIKE ?)
              AND (
                   NOT EXISTS (SELECT 1 FROM product_regions pr WHERE pr.product_id = p.id)
                OR EXISTS (SELECT 1 FROM product_regions pr WHERE pr.product_id = p.id AND pr.region_id = ?)
              )
            ORDER BY p.id DESC
        ''', (like, like, region_id)).fetchall()
    else:
        # No region selected + Search term: Show all matching products from Products category only
        all_products = conn.execute('SELECT * FROM products WHERE (name LIKE ? OR description LIKE ?) AND category = "Products" ORDER BY id DESC', (like, like)).fetchall()
    
    # Filter by product status if selected (but not if 'all' is selected)
    if product_status and product_status != 'all':
        all_products = [p for p in all_products if p['product_status'] == product_status]
    
    # Sorting for search results
    if sort == 'price_low':
        all_products = sorted(all_products, key=lambda p: (p['price'] or 0))
    elif sort == 'price_high':
        all_products = sorted(all_products, key=lambda p: (p['price'] or 0), reverse=True)
    elif sort == 'name_az':
        all_products = sorted(all_products, key=lambda p: (p['name'] or '').lower())
    
    conn.close()
    
    # Pagination logic
    total_products = len(all_products)
    total_pages = (total_products + PRODUCTS_PER_PAGE - 1) // PRODUCTS_PER_PAGE
    
    if page > total_pages and total_pages > 0:
        page = total_pages
    
    start_idx = (page - 1) * PRODUCTS_PER_PAGE
    end_idx = start_idx + PRODUCTS_PER_PAGE
    products = all_products[start_idx:end_idx]
    
    # Bulk review stats for visible products (for star display on cards)
    review_stats_map = compute_review_stats_bulk([p['id'] for p in products])
    # Mark first 4 from ALL results as "new"
    new_product_ids = {p['id'] for p in all_products[:4]}
    
    return render_template('index.html', 
                         products=products, 
                         new_product_ids=new_product_ids,
                         title=f"Search: {q}", 
                         is_search_result=True,
                         search_query=q,
                         current_page=page,
                         total_pages=total_pages,
                         total_products=total_products,
                         review_stats_map=review_stats_map,
                         sort=sort)

########################
# Robots and Sitemap
########################

@app.get('/robots.txt')
def robots_txt():
    content = "User-agent: *\nAllow: /\n"
    return (content, 200, {'Content-Type': 'text/plain; charset=utf-8'})

@app.get('/sitemap.xml')
def sitemap_xml():
    base = SITE_BASE_URL or request.url_root.rstrip('/')
    urls = [
        f"{base}/",
        f"{base}/cart",
        f"{base}/checkout",
        f"{base}/user/login",
        f"{base}/user/register",
        f"{base}/admin/login",
        f"{base}/customer-care/shipping",
        f"{base}/customer-care/returns",
        f"{base}/customer-care/contact",
    ]
    conn = get_db()
    products = conn.execute('SELECT id FROM products ORDER BY id DESC').fetchall()
    conn.close()
    for p in products:
        urls.append(f"{base}/product/{p['id']}")
    xml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]
    for u in urls:
        xml.append('<url>')
        xml.append(f'<loc>{u}</loc>')
        xml.append('</url>')
    xml.append('</urlset>')
    return ("\n".join(xml), 200, {'Content-Type': 'application/xml; charset=utf-8'})

@app.post('/set_region')
def set_region():
    rid = request.form.get('region_id')
    try:
        if rid == 'all':
            # "All Regions" selected - store as string to indicate all regions
            session['region_id'] = 'all'
            flash('Showing all regions', 'success')
        elif rid:
            rid_int = int(rid)
            session['region_id'] = rid_int
            flash('Region updated', 'success')
        else:
            session.pop('region_id', None)
            flash('Region cleared', 'success')
    except (ValueError, Exception):
        session.pop('region_id', None)
        flash('Region cleared', 'success')
    return redirect(request.referrer or url_for('index'))


@app.post('/set_product_status')
def set_product_status():
    ps = request.form.get('product_status')
    try:
        if ps == 'all':
            # "All Status" selected - store as string to indicate all statuses
            session['product_status'] = 'all'
            flash('Showing all statuses', 'success')
        elif ps and ps in VALID_PRODUCT_STATUSES:
            session['product_status'] = ps
            flash(f'Filtered by: {ps}', 'success')
        else:
            session.pop('product_status', None)
            flash('Status filter cleared', 'success')
    except Exception:
        session.pop('product_status', None)
        flash('Status filter cleared', 'success')
    return redirect(request.referrer or url_for('index'))

@app.route('/reset_filters')
def reset_filters():
    """Reset all filters (region and product status) when user clicks Home"""
    session.pop('region_id', None)
    session.pop('product_status', None)
    flash('Filters reset', 'success')
    return redirect(url_for('index'))


@app.route('/product/<int:pid>')
def product_detail(pid):
    conn = get_db()
    product = conn.execute(SQL_SELECT_PRODUCT_BY_ID, (pid,)).fetchone()
    conn.close()
    if not product:
        flash(MSG_PRODUCT_NOT_FOUND, 'error')
        return redirect(url_for('index'))
    
    # Get all catalog images for the product
    product_images = get_product_images(pid)
    # Reviews context
    sort = request.args.get('sort', 'helpful')
    try:
        page = max(1, int(request.args.get('page', '1')))
    except Exception:
        page = 1
    page_size = 5
    offset = (page - 1) * page_size
    review_stats = compute_review_stats(pid)
    reviews = fetch_product_reviews(pid, sort=sort, limit=page_size, offset=offset)
    
    return render_template(
        'product_detail.html',
        product=product,
        est_date=calculate_estimated_date(product),
        catalog_images=product_images,
        review_stats=review_stats,
        reviews=reviews,
        review_sort=sort,
        review_page=page,
        review_page_size=page_size
    )


@app.route('/add_to_cart/<int:pid>')
def add_to_cart(pid):
    conn = get_db()
    p = conn.execute(SQL_SELECT_PRODUCT_BY_ID, (pid,)).fetchone()
    conn.close()
    if not p:
        flash(MSG_PRODUCT_NOT_FOUND, 'error')
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


# ==========================
# Reviews routes
# ==========================

@app.route('/product/<int:pid>/reviews/new', methods=['POST'])
def submit_review(pid):
    # Require login to post a review
    if not session.get('user_logged_in'):
        flash('Please log in to post a review.', 'error')
        return redirect(url_for('user_login'))

    rating_str = request.form.get('rating', '').strip()
    title = request.form.get('title', '').strip()
    body = request.form.get('body', '').strip()

    # Basic validation
    try:
        rating = int(rating_str)
    except Exception:
        rating = 0
    errors = []
    if rating < 1 or rating > 5:
        errors.append('Please provide a rating between 1 and 5 stars.')
    if len(body) < 10:
        errors.append('Review must be at least 10 characters long.')

    # Ensure product exists
    conn = get_db()
    product = conn.execute(SQL_SELECT_PRODUCT_BY_ID, (pid,)).fetchone()
    if not product:
        conn.close()
        flash(MSG_PRODUCT_NOT_FOUND, 'error')
        return redirect(url_for('index'))

    if errors:
        for e in errors:
            flash(e, 'error')
        conn.close()
        return redirect(url_for('product_detail', pid=pid))

    user_id = session.get('user_id')
    email = session.get('user_email')
    verified = 1 if user_verified_purchase(email, pid) else 0
    now = datetime.now().isoformat()

    try:
        conn.execute(
            'INSERT INTO product_reviews (product_id, user_id, rating, title, body, verified_purchase, helpful_count, is_approved, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 0, 1, ?, ?)',
            (pid, user_id, rating, title, body, verified, now, now)
        )
        conn.commit()
        flash('Thanks for your review!', 'success')
    except Exception as e:
        flash(f'Failed to submit review: {str(e)}', 'error')
    finally:
        conn.close()

    return redirect(url_for('product_detail', pid=pid))


@app.route('/reviews/<int:rid>/helpful', methods=['POST'])
def mark_review_helpful(rid):
    if not session.get('user_logged_in'):
        flash('Please log in to vote reviews.', 'error')
        return redirect(url_for('user_login'))

    user_id = session.get('user_id')
    conn = get_db()
    try:
        # Find review and product
        review = conn.execute('SELECT id, product_id FROM product_reviews WHERE id=?', (rid,)).fetchone()
        if not review:
            conn.close()
            flash('Review not found', 'error')
            return redirect(url_for('index'))

        # Prevent duplicate votes
        existing = conn.execute('SELECT id FROM review_votes WHERE review_id=? AND user_id=?', (rid, user_id)).fetchone()
        if existing:
            flash('You already marked this review as helpful.', 'info')
            conn.close()
            return redirect(url_for('product_detail', pid=review['product_id']))

        # Insert vote and increment counter
        now = datetime.now().isoformat()
        conn.execute('INSERT INTO review_votes (review_id, user_id, vote, created_at) VALUES (?, ?, 1, ?)', (rid, user_id, now))
        conn.execute('UPDATE product_reviews SET helpful_count = helpful_count + 1 WHERE id=?', (rid,))
        conn.commit()
        flash('Marked helpful. Thank you!', 'success')
        return redirect(url_for('product_detail', pid=review['product_id']))
    except Exception as e:
        conn.rollback()
        flash(f'Failed to vote: {str(e)}', 'error')
        return redirect(request.referrer or url_for('index'))
    finally:
        conn.close()


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
            pr = conn.execute(SQL_SELECT_PRODUCT_BY_ID, (item['id'],)).fetchone()
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
        user = conn.execute(SQL_SELECT_USER_BY_ID, (user_id,)).fetchone()
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
# Newsletter subscription
########################

def subscribe_brevo(email: str) -> bool:
    """Subscribe an email to Brevo list if configured. Returns True on API success or if not configured."""
    if not BREVO_API_KEY or not BREVO_LIST_ID or not requests:
        return True
    try:
        url = 'https://api.brevo.com/v3/contacts'
        headers = {
            'accept': 'application/json',
            'content-type': 'application/json',
            'api-key': BREVO_API_KEY,
        }
        payload = {
            'email': email,
            'listIds': [int(BREVO_LIST_ID)],
            'updateEnabled': True,
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        return resp.status_code in (200, 201)
    except Exception:
        return False


@app.post('/subscribe')
def subscribe():
    email = (request.form.get('email') or '').strip().lower()
    if not email or '@' not in email:
        flash('Please enter a valid email.', 'error')
        return redirect(request.referrer or url_for('index'))
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute('INSERT OR IGNORE INTO newsletter_subscribers (email, created_at) VALUES (?, ?)', (email, datetime.now().isoformat()))
        conn.commit(); conn.close()
    except Exception:
        flash('Unable to save your subscription right now.', 'error')
        return redirect(request.referrer or url_for('index'))
    if subscribe_brevo(email):
        flash('Subscribed! Check your inbox for updates.', 'success')
    else:
        flash('Subscribed locally. We will add you to our mailing list shortly.', 'success')
    return redirect(request.referrer or url_for('index'))

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
        user = conn.execute(SQL_SELECT_USER_BY_EMAIL, (email,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session.permanent = True
            session['user_logged_in'] = True
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            session['user_name'] = user['full_name']
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
    user = conn.execute(SQL_SELECT_USER_BY_ID, (user_id,)).fetchone()
    
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
    orders = conn.execute(SQL_SELECT_ORDERS_BY_EMAIL, (email,)).fetchall()
    conn.close()
    return render_template('user_orders.html', orders=orders)

########################
# Admin routes
########################

def is_admin():
    return session.get('admin_logged_in') is True


@app.route('/admin/diagnose')
def admin_diagnose():
    """Diagnostic endpoint to check admin user status (debugging only)"""
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Check if admin_users table exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_users'")
    table_exists = cur.fetchone() is not None
    
    # Get admin users
    admin_users = []
    if table_exists:
        cur.execute('SELECT id, username FROM admin_users')
        admin_users = [dict(row) for row in cur.fetchall()]
    
    conn.close()
    
    env_password = os.environ.get('ADMIN_DEFAULT_PASSWORD', 'NOT SET')
    
    return {
        'admin_users_table_exists': table_exists,
        'admin_users': admin_users,
        'admin_default_password_set': env_password != 'NOT SET',
        'env_password_value': env_password,
        'db_path': DB_PATH,
        'db_exists': os.path.exists(DB_PATH)
    }


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        print(f"\n[DEBUG LOGIN] Attempting login with username: '{username}'")
        
        conn = get_db()
        admin = conn.execute('SELECT * FROM admin_users WHERE username=?', (username,)).fetchone()
        conn.close()
        
        # Debug: Check if admin exists
        if not admin:
            print(f"[DEBUG LOGIN] ❌ Admin user '{username}' not found in database")
            flash('Invalid credentials', 'error')
            return render_template('admin_login.html')
        
        print(f"[DEBUG LOGIN] ✅ Admin user '{username}' found in database")
        
        # Check password hash
        if not admin['password_hash']:
            print(f"[DEBUG LOGIN] ❌ Admin user '{username}' has empty password_hash")
            flash('Invalid credentials', 'error')
            return render_template('admin_login.html')
        
        # Try to verify password hash
        try:
            if check_password_hash(admin['password_hash'], password):
                print(f"[DEBUG LOGIN] ✅ Password verification successful for '{username}'")
                session.permanent = True
                session['admin_logged_in'] = True
                session['admin_username'] = username
                flash('Welcome, admin!', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                print(f"[DEBUG LOGIN] ❌ Password verification failed for '{username}'")
                print(f"[DEBUG LOGIN]    Password entered: '{password}'")
                print(f"[DEBUG LOGIN]    Hash in DB: {admin['password_hash'][:40]}...")
        except Exception as e:
            print(f"[DEBUG LOGIN] ❌ Error during password verification: {e}")
        
        flash('Invalid credentials', 'error')
        return render_template('admin_login.html')
    
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
        'subscribers': conn.execute('SELECT COUNT(*) as c FROM newsletter_subscribers').fetchone()['c'],
    }
    conn.close()
    return render_template('admin_dashboard.html', stats=stats)


@app.route('/admin/products')
def admin_products():
    if not is_admin():
        return redirect(url_for('admin_login'))
    
    conn = get_db()
    conn.row_factory = sqlite3.Row
    
    # Get all regions for filter dropdown
    regions = conn.execute('SELECT id, name FROM regions ORDER BY name').fetchall()
    
    # Get filter parameters from request
    search_query = request.args.get('search', '').strip()
    selected_region = request.args.get('region', '')
    selected_category = request.args.get('category', '')
    
    # Build query based on filters
    query = 'SELECT DISTINCT p.* FROM products p'
    params = []
    where_clauses = []
    
    # Add region filter if selected
    if selected_region:
        query += ' LEFT JOIN product_regions pr ON p.id = pr.product_id'
        where_clauses.append('(pr.region_id = ? OR pr.region_id IS NULL)')
        params.append(selected_region)
    
    # Add category filter if selected
    if selected_category:
        where_clauses.append('p.category = ?')
        params.append(selected_category)
    
    # Add search filter if provided
    if search_query:
        where_clauses.append('(p.name LIKE ? OR p.description LIKE ?)')
        params.append(f'%{search_query}%')
        params.append(f'%{search_query}%')
    
    # Combine where clauses
    if where_clauses:
        query += ' WHERE ' + ' AND '.join(where_clauses)
    
    query += ' ORDER BY p.id DESC'
    
    products = conn.execute(query, params).fetchall()
    
    # For each product, get its regions
    products_with_regions = []
    for product in products:
        product_regions = conn.execute(
            'SELECT r.id, r.name FROM regions r JOIN product_regions pr ON r.id = pr.region_id WHERE pr.product_id = ? ORDER BY r.name',
            [product['id']]
        ).fetchall()
        products_with_regions.append({
            'product': product,
            'regions': product_regions
        })
    
    conn.close()
    
    # Available categories
    categories = ['Products', 'Gut Care', 'Corporate', 'Gifts']
    
    return render_template('admin_products.html', 
                         products=products_with_regions, 
                         regions=regions,
                         categories=categories,
                         search_query=search_query,
                         selected_region=selected_region,
                         selected_category=selected_category)


@app.route('/admin/product/new', methods=['GET', 'POST'])
def admin_product_new():
    if not is_admin():
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price_str = request.form.get('price', '').strip()
        mrp_str = request.form.get('mrp', '').strip()
        size = request.form.get('size', 'Standard').strip()
        stock = int(request.form.get('stock', '0'))
        est_days = request.form.get('estimated_delivery_days')
        est_date = request.form.get('estimated_delivery_date')
        is_homepage = 1 if request.form.get('is_homepage') else 0
        product_status = request.form.get('product_status', 'Final Product')
        category = request.form.get('category', 'Products').strip()
        selected_regions = request.form.getlist('regions')
        
        # If no regions selected, default to 'all' (meaning all regions)
        if not selected_regions:
            selected_regions = ['all']
        
        # Validation: Check mandatory fields
        errors = []
        if not name:
            errors.append('Product name is required')
        if not description:
            errors.append('Product description is required')
        if not price_str:
            errors.append('Product price is required')
        else:
            try:
                price = float(price_str)
                if price < 0:
                    errors.append('Price must be a positive number')
            except ValueError:
                errors.append('Price must be a valid number')
        # Optional MRP validation
        mrp = None
        if mrp_str:
            try:
                mrp = float(mrp_str)
                if mrp < 0:
                    errors.append('MRP must be a positive number')
                elif 'price' in locals() and mrp < price:
                    errors.append('MRP should be greater than or equal to Price')
            except ValueError:
                errors.append('MRP must be a valid number')
        
        # Check if image is provided
        if 'image' not in request.files or request.files['image'].filename == '':
            errors.append('Product image is required')
        
        # If any validation errors, return form with errors
        if errors:
            for error in errors:
                flash(error, 'error')
            conn = get_db()
            regions = conn.execute(SQL_SELECT_REGION_ID_NAME_ORDERED).fetchall()
            conn.close()
            return render_template('admin_product_form.html', product={
                'name': name, 'description': description, 'price': price_str, 'mrp': mrp_str,
                'stock': stock, 'estimated_delivery_days': est_days,
                'estimated_delivery_date': est_date, 'is_homepage': is_homepage,
                'product_status': product_status
            }, regions=regions, selected_regions=selected_regions)
        
        # All validation passed, proceed with product creation
        price = float(price_str)
        
        # Create the product first to get its ID
        conn = get_db()
        cursor = conn.execute(
            'INSERT INTO products (name, description, price, mrp, size, stock, estimated_delivery_days, estimated_delivery_date, is_homepage, product_status, category) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (name, description, price, mrp if mrp is not None else None, size, stock, est_days if est_days else None, est_date if est_date else None, is_homepage, product_status, category)
        )
        conn.commit()
        product_id = cursor.lastrowid
        conn.close()

        # Save image and attach to product
        if 'image' in request.files and request.files['image'].filename != '':
            file = request.files['image']
            image_path = save_product_image(file, product_id)
            if image_path:
                conn = get_db()
                conn.execute('UPDATE products SET image_path=? WHERE id=?', (image_path, product_id))
                conn.commit(); conn.close()
        
        # Assign regions - if 'all' was selected, assign to all active regions
        if 'all' in selected_regions:
            conn = get_db()
            all_regions = conn.execute(SQL_SELECT_REGION_ID_NAME_ORDERED).fetchall()
            conn.close()
            all_region_ids = [str(r['id']) for r in all_regions]
            set_product_regions(product_id, all_region_ids)
        else:
            set_product_regions(product_id, selected_regions)
        
        flash('Product created successfully', 'success')
        return redirect(url_for('admin_products'))
    # GET: show form with regions
    conn = get_db()
    regions = conn.execute(SQL_SELECT_REGION_ID_NAME_ORDERED).fetchall()
    conn.close()
    return render_template('admin_product_form.html', product=None, regions=regions, selected_regions=['all'])


@app.route('/admin/product/<int:pid>/edit', methods=['GET', 'POST'])
def admin_product_edit(pid):
    if not is_admin():
        return redirect(url_for('admin_login'))
    conn = get_db()
    product = conn.execute(SQL_SELECT_PRODUCT_BY_ID, (pid,)).fetchone()
    if not product:
        conn.close()
        flash('Product not found', 'error')
        return redirect(url_for('admin_products'))
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = float(request.form.get('price', '0'))
        mrp_str = request.form.get('mrp', '').strip()
        mrp_val = None
        try:
            if mrp_str:
                mrp_val = float(mrp_str)
        except Exception:
            mrp_val = None
        size = request.form.get('size', 'Standard').strip()
        stock = int(request.form.get('stock', '0'))
        est_days = request.form.get('estimated_delivery_days')
        est_date = request.form.get('estimated_delivery_date')
        is_homepage = 1 if request.form.get('is_homepage') else 0
        product_status = request.form.get('product_status', 'Final Product')
        category = request.form.get('category', 'Products').strip()
        
        # Handle image upload (replace previous image if new one provided)
        image_path = product['image_path']
        uploaded = request.files.get('image')
        if uploaded and uploaded.filename != '':
            image_path = replace_product_image(pid, image_path, uploaded)

        conn.execute('UPDATE products SET name=?, description=?, price=?, mrp=?, size=?, stock=?, estimated_delivery_days=?, estimated_delivery_date=?, image_path=?, is_homepage=?, product_status=?, category=? WHERE id=?',
                     (name, description, price, mrp_val, size, stock, est_days if est_days else None, est_date if est_date else None, image_path, is_homepage, product_status, category, pid))
        conn.commit()
        # Update regions mapping
        selected_regions = request.form.getlist('regions')
        if not selected_regions:
            selected_regions = ['all']
        
        # If 'all' was selected, assign to all active regions
        if 'all' in selected_regions:
            all_regions = conn.execute(SQL_SELECT_REGION_ID_NAME_ORDERED).fetchall()
            all_region_ids = [str(r['id']) for r in all_regions]
            set_product_regions(pid, all_region_ids)
        else:
            set_product_regions(pid, selected_regions)
        
        flash('Product updated', 'success')
        return redirect(url_for('admin_products'))
    # GET: load regions and selected for this product
    selected = conn.execute('SELECT region_id FROM product_regions WHERE product_id=?', (pid,)).fetchall()
    regions = conn.execute(SQL_SELECT_REGION_ID_NAME_ORDERED).fetchall()
    conn.close()
    selected_ids = [row['region_id'] for row in selected]
    # If no regions selected, show 'all' as pre-selected
    if not selected_ids:
        selected_ids = ['all']
    return render_template('admin_product_form.html', product=product, regions=regions, selected_regions=selected_ids)


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


@app.route('/admin/subscribers')
def admin_subscribers():
    if not is_admin():
        return redirect(url_for('admin_login'))
    conn = get_db()
    subs = conn.execute('SELECT * FROM newsletter_subscribers ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('admin_subscribers.html', subscribers=subs)


@app.route('/admin/catalog-images')
def admin_catalog_images():
    if not is_admin():
        return redirect(url_for('admin_login'))
    conn = get_db()
    images = conn.execute('SELECT * FROM catalog_images ORDER BY region').fetchall()
    conn.close()
    return render_template('admin_catalog_images.html', images=images)


@app.post('/admin/catalog-images/upload')
def admin_catalog_images_upload():
    if not is_admin():
        return redirect(url_for('admin_login'))
    
    region = request.form.get('region')  # 'left', 'right', or 'hero'
    alt_text = request.form.get('alt_text', 'Catalog Image')
    file = request.files.get('image')
    
    if not region or region not in ['left', 'right', 'hero']:
        flash('Invalid region selected', 'error')
        return redirect(url_for('admin_catalog_images'))
    
    if not file or file.filename == '':
        flash('No image selected', 'error')
        return redirect(url_for('admin_catalog_images'))
    
    image_path = save_product_image(file, f'catalog_{region}')
    if not image_path:
        flash('Error uploading image', 'error')
        return redirect(url_for('admin_catalog_images'))
    
    conn = get_db()
    try:
        # Find next available position (1-4)
        max_pos = conn.execute(
            'SELECT MAX(position) as max_pos FROM catalog_images WHERE region=?',
            (region,)
        ).fetchone()
        
        next_position = (max_pos['max_pos'] or 0) + 1
        
        # Check if we already have 4 images
        count = conn.execute(
            'SELECT COUNT(*) as cnt FROM catalog_images WHERE region=?',
            (region,)
        ).fetchone()['cnt']
        
        if count >= 4:
            flash('Maximum 4 images allowed per region', 'error')
            os.remove(os.path.join('static', image_path))
            conn.close()
            return redirect(url_for('admin_catalog_images'))
        
        # Insert new image
        conn.execute(
            'INSERT INTO catalog_images (region, position, image_path, alt_text, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)',
            (region, next_position, image_path, alt_text, datetime.now().isoformat(), datetime.now().isoformat())
        )
        conn.commit()
        flash(f'Image #{next_position} added to {region.capitalize()} region', 'success')
    except Exception as e:
        flash(f'Error saving image: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('admin_catalog_images'))


@app.post('/admin/catalog-images/<region>/<int:position>/delete')
def admin_catalog_images_delete(region, position):
    if not is_admin():
        return redirect(url_for('admin_login'))
    
    if region not in ['left', 'right', 'hero']:
        flash('Invalid region', 'error')
        return redirect(url_for('admin_catalog_images'))
    
    conn = get_db()
    try:
        image_data = conn.execute('SELECT image_path FROM catalog_images WHERE region=? AND position=?', (region, position)).fetchone()
        if image_data:
            image_path = image_data['image_path']
            filepath = os.path.join('static', image_path)
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except OSError:
                    pass
            conn.execute('DELETE FROM catalog_images WHERE region=? AND position=?', (region, position))
            conn.commit()
            flash(f'Image deleted from {region.capitalize()} region', 'success')
        else:
            flash('Image not found', 'error')
    except Exception as e:
        flash(f'Error deleting image: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('admin_catalog_images'))


@app.post('/admin/subscribers/<int:sid>/delete')
def admin_subscriber_delete(sid):
    if not is_admin():
        return redirect(url_for('admin_login'))
    conn = get_db()
    conn.execute('DELETE FROM newsletter_subscribers WHERE id=?', (sid,))
    conn.commit(); conn.close()
    flash('Subscriber deleted', 'success')
    return redirect(url_for('admin_subscribers'))


@app.get('/admin/subscribers/export')
def admin_subscribers_export():
    if not is_admin():
        return redirect(url_for('admin_login'))
    conn = get_db()
    rows = conn.execute('SELECT email, created_at FROM newsletter_subscribers ORDER BY id DESC').fetchall()
    conn.close()
    # Build CSV
    csv_lines = ['email,created_at']
    for r in rows:
        email = r['email'] or ''
        created = r['created_at'] or ''
        # escape commas minimally (not expecting commas in email)
        csv_lines.append(f"{email},{created}")
    csv_data = "\n".join(csv_lines)
    return (csv_data, 200, {
        'Content-Type': 'text/csv; charset=utf-8',
        'Content-Disposition': 'attachment; filename="newsletter_subscribers.csv"'
    })


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
