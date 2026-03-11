from flask import Flask, render_template, session, request, redirect, url_for, jsonify, flash
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO
from datetime import datetime
from decimal import Decimal
import mysql.connector
import traceback
import random
import string
import logging
import os

app = Flask(__name__)
app.secret_key = 'prime_cart_secret'
socketio = SocketIO(app, cors_allowed_origins="*")

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
last_rfid = None

# MySQL configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '1234',
    'database': 'primecart',
    'use_pure': True
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

def safe_route(func):
    """Decorator to wrap routes with try/except"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print("Error in route:", func.__name__)
            traceback.print_exc()
            return f"An error occurred: {e}", 500
    wrapper.__name__ = func.__name__
    return wrapper

@app.route('/')
def home():
    # =====================
    # Default cart items
    # =====================
    total_cart_items = 0

    # =====================
    # Database connection
    # =====================
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # =====================
    # Fetch categories with product counts
    # =====================
    cursor.execute("""
        SELECT category, COUNT(*) AS product_count
        FROM products
        GROUP BY category
        ORDER BY product_count DESC
    """)
    categories = cursor.fetchall()

    category_icons = {
        "Electronics": "fas fa-laptop",
        "Fashion": "fas fa-tshirt",
        "Home & Kitchen": "fas fa-home",
        "Sports & Outdoors": "fas fa-dumbbell",
        "Books & Media": "fas fa-book",
        "Baby & Kids": "fas fa-baby",
        "Automotive": "fas fa-car",
        "Gaming": "fas fa-gamepad"
    }

    # Decode bytes & add icons
    for cat in categories:
        if isinstance(cat['category'], bytes):
            cat['category'] = cat['category'].decode('utf-8')
        cat['icon'] = category_icons.get(cat['category'], 'fas fa-box')

    # =====================
    # Fetch latest products
    # =====================
    cursor.execute("""
        SELECT id, name, category, price, stock, status, description, image, rfid_tag
        FROM products
        ORDER BY created_at DESC
        LIMIT 8
    """)
    products = cursor.fetchall()

    # Decode bytes to strings for products
    for prod in products:
        for key in ['name', 'category', 'status', 'description', 'image', 'rfid_tag']:
            if isinstance(prod[key], bytes):
                prod[key] = prod[key].decode('utf-8')

    cursor.close()
    conn.close()

    # =====================
    # Fetch user info if logged in
    # =====================
    user_info = None
    if 'user_id' in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if session.get('role') == 'admin':
            cursor.execute("SELECT id, username, full_name, email FROM users WHERE id = %s", (session['user_id'],))
        else:
            cursor.execute("SELECT id, name AS full_name, email FROM customers WHERE id = %s", (session['user_id'],))
        user_info = cursor.fetchone()

        # Decode user fields if needed
        if user_info:
            for key, value in user_info.items():
                if isinstance(value, bytes):
                    user_info[key] = value.decode('utf-8')

        # Fetch total cart items
        cursor.execute("""
            SELECT SUM(quantity) AS total_items
            FROM cart
            WHERE user_id = %s
        """, (session['user_id'],))
        result = cursor.fetchone()
        total_cart_items = int(result['total_items'] or 0)

        cursor.close()
        conn.close()

    # =====================
    # Render template
    # =====================
    return render_template(
        'home.html',
        categories=categories,
        products=products,
        user=user_info,
        total_cart_items=total_cart_items  # now always defined
    )

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        data = request.get_json()

        # Map JS fields to Python
        first_name = data.get('first_name') or data.get('firstName')
        last_name = data.get('last_name') or data.get('lastName')
        name = f"{first_name} {last_name}"
        email = data.get('email')
        phone = data.get('phone')
        password = data.get('password')
        newsletter = data.get('newsletter', True)
        sms_alerts = data.get('sms_alerts', False)

        password_hash = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Check if email exists
        cursor.execute("SELECT id FROM customers WHERE email=%s", (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'status': 'error', 'message': 'Email already exists'})

        cursor.execute("""
            INSERT INTO customers (name, email, phone, password_hash, newsletter, sms_alerts)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (name, email, phone, password_hash, newsletter, sms_alerts))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'status': 'success', 'message': 'Account created successfully'})

    return render_template('signup.html')

# ---------------- Login ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 1️⃣ Check USERS table
        cursor.execute("""
            SELECT id, username, email, role, password_hash, full_name 
            FROM users 
            WHERE email = %s
        """, (email,))
        user = cursor.fetchone()
        
        print(user)

        if user and check_password_hash(user['password_hash'], password):
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user.get('username') or user.get('full_name')
            session['role'] = user['role']

            cursor.close()
            conn.close()

            # Determine dashboard based on role
            if user['role'] == 'admin':
                redirect_url = '/admin/dashboard'
            elif user['role'] == 'seller':
                redirect_url = '/seller/dashboard'
            elif user['role'] == 'delivery_agent':
                redirect_url = '/delivery/dashboard'
            else:
                redirect_url = '/'

            return jsonify({'status': 'success', 'role': user['role'], 'redirect': redirect_url})

        # 2️⃣ Check CUSTOMERS table
        cursor.execute("""
            SELECT id, name, email, password_hash, status 
            FROM customers 
            WHERE email=%s
        """, (email,))
        customer = cursor.fetchone()
        cursor.close()
        conn.close()

        if customer:
            if customer['status'] != 'active':
                return jsonify({'status': 'error', 'message': 'Account is inactive or blocked'})
            if check_password_hash(customer['password_hash'], password):
                session.clear()
                session['user_id'] = customer['id']  # use same key as admin for template consistency
                session['role'] = 'customer'
                session['username'] = customer['name']

                return jsonify({'status': 'success', 'role': 'customer', 'redirect': '/'})

        return jsonify({'status': 'error', 'message': 'Invalid email or password'})

    return render_template('login.html')


# ---------------- Admin Dashboard ----------------
@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Products
    cursor.execute("SELECT id, name, category, price, stock FROM products ORDER BY created_at DESC LIMIT 5")
    products = cursor.fetchall()

    # Orders
    cursor.execute("""
        SELECT o.id, o.order_number, c.name AS customer_name, o.created_at, o.total_amount, o.status
        FROM orders o
        LEFT JOIN customers c ON o.customer_id = c.id
        ORDER BY o.created_at DESC
        LIMIT 5
    """)
    orders = cursor.fetchall()

    # Stats
    cursor.execute("SELECT COUNT(*) AS total_orders FROM orders")
    total_orders = cursor.fetchone()['total_orders']

    cursor.execute("SELECT SUM(total_amount) AS total_revenue FROM orders")
    total_revenue = cursor.fetchone()['total_revenue'] or 0

    cursor.execute("SELECT COUNT(*) AS total_customers FROM customers")
    total_customers = cursor.fetchone()['total_customers']

    cursor.execute("SELECT COUNT(*) AS low_stock_items FROM products WHERE stock < 5")
    low_stock_items = cursor.fetchone()['low_stock_items']

    cursor.close()
    conn.close()

    stats = {
        'total_orders': total_orders,
        'revenue': total_revenue,
        'customers': total_customers,
        'low_stock': low_stock_items
    }

    return render_template('admin/dashboard.html', products=products, orders=orders, stats=stats)

scan_active = False

@app.route("/start_scan", methods=["POST"])
def start_scan():
    global scan_active
    scan_active = True
    socketio.emit("start_scan", {"action":"start_scan"})
    logging.basicConfig(level=logging.INFO)
    logging.info("Scan requested from browser")
    return jsonify({"status":"scan_started"})

@app.route("/rfid", methods=["POST","GET"])
def receive_rfid():
    global scan_active, last_rfid   # ✅ FIX IS HERE

    try:
        data = request.get_json(force=True)
        rfid = data.get("rfid")

        if not rfid:
            return jsonify({"status":"error","message":"No RFID sent"}), 400

        print("📡 RFID received:", rfid)

        scan_active = False
        last_rfid = rfid  # ✅ Now stored globally

        socketio.emit("rfid_scanned", {"rfid": rfid})

        return jsonify({"status":"ok"})

    except Exception as e:
        print("❌ Error in /rfid:", e)
        return jsonify({"status":"error","message": str(e)}), 500


@app.route("/rfid_last")
def get_last_rfid():
    global last_rfid
    try:
        print("DEBUG RFID VALUE:", last_rfid)

        if last_rfid:
            return jsonify({"rfid": last_rfid})

        return jsonify({"rfid": None})

    except Exception as e:
        print("RFID ERROR:", str(e))
        return jsonify({"error": "RFID fetch failed"}), 500



@app.route("/esp/scan_status")
def esp_scan_status():
    return jsonify(scan=scan_active)

# ---------------- Add Products ----------------
@app.route('/admin/add-product', methods=['POST'])
def add_product():
    if session.get('role') != 'admin':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403

    try:
        # =====================
        # Get form data
        # =====================
        name = request.form.get('name')
        category = request.form.get('category')
        price = float(request.form.get('price', 0))
        stock = int(request.form.get('stock', 0))
        description = request.form.get('description', '')
        rfid_tag = request.form.get('rfid_tag', '')

        # Validate required fields
        if not all([name, category, price, stock, rfid_tag]):
            return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400

        # =====================
        # Stock status
        # =====================
        if stock == 0:
            status = 'Out of Stock'
        elif stock <= 5:
            status = 'Low Stock'
        else:
            status = 'In Stock'

        # =====================
        # Image handling
        # =====================
        image = request.files.get('image')
        if not image:
            return jsonify({'status': 'error', 'message': 'Image is required'}), 400

        filename = secure_filename(image.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(save_path)

        # =====================
        # Save to database
        # =====================
        conn = get_db_connection()
        cursor = conn.cursor()

        # Optional: check if RFID already exists
        cursor.execute("SELECT id FROM products WHERE rfid_tag = %s", (rfid_tag,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'status': 'error', 'message': 'RFID tag already used'}), 400

        cursor.execute("""
            INSERT INTO products
            (name, category, price, stock, status, description, rfid_tag, image)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            name,
            category,
            price,
            stock,
            status,
            description,
            rfid_tag,
            filename
        ))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'status': 'success', 'message': 'Product added successfully'})

    except Exception as e:
        print("Error adding product:", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500

from flask import session, redirect, url_for

@app.route('/buy/<int:product_id>')
def buy_product(product_id):
    # Check if user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))  # redirect to login page

    user_id = session['user_id']

    # Add product to cart in database
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if product already in cart
    cursor.execute("""
        SELECT id, quantity FROM cart
        WHERE user_id = %s AND product_id = %s
    """, (user_id, product_id))
    existing = cursor.fetchone()

    if existing:
        # If already in cart, increment quantity
        cursor.execute("""
            UPDATE cart
            SET quantity = quantity + 1
            WHERE id = %s
        """, (existing[0],))
    else:
        # Insert new row in cart
        cursor.execute("""
            INSERT INTO cart (user_id, product_id, quantity)
            VALUES (%s, %s, 1)
        """, (user_id, product_id))

    conn.commit()
    cursor.close()
    conn.close()

    # Redirect to cart page
    return redirect(url_for('cart'))


@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch cart items
    cursor.execute("""
        SELECT 
            c.id AS cart_id,
            c.quantity,
            p.id AS product_id,
            p.name,
            p.category,
            p.price,
            p.stock,
            p.image,
            p.rfid_tag,
            p.description
        FROM cart c
        JOIN products p ON c.product_id = p.id
        WHERE c.user_id = %s
        ORDER BY c.added_at DESC
    """, (user_id,))
    
    cart_items = cursor.fetchall()
    cursor.close()
    conn.close()

    # Fix image and price types
    for item in cart_items:
        if isinstance(item['image'], (bytes, bytearray)):
            item['image'] = item['image'].decode('utf-8')
        if isinstance(item['price'], Decimal):
            item['price'] = float(item['price'])

    # Calculate totals
    subtotal = sum(item['price'] * item['quantity'] for item in cart_items)
    shipping = 12.99 if subtotal > 0 else 0.0  # example flat shipping
    tax = round(subtotal * 0.08, 2)  # 8% tax
    savings = round(sum(item['price'] * item['quantity'] * 0.1 for item in cart_items), 2)  # example 10% off
    order_total = round(subtotal + shipping + tax - savings, 2)
    
    total_items = sum(item['quantity'] for item in cart_items)

    return render_template(
        'cart.html', 
        cart_items=cart_items,
        subtotal=subtotal,
        shipping=shipping,
        tax=tax,
        savings=savings,
        order_total=order_total,
        total_items=total_items
    )


@app.route('/cart/delete/<int:cart_id>')
def delete_cart_item(cart_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor()

    # Delete only if the item belongs to the logged-in user
    cursor.execute("""
        DELETE FROM cart 
        WHERE id = %s AND user_id = %s
    """, (cart_id, user_id))

    conn.commit()
    cursor.close()
    conn.close()

    # Redirect back to the cart page
    return redirect(url_for('cart'))

def generate_order_number():
    """Generate a random order number e.g., ORD-20260131-AB12"""
    date_str = datetime.now().strftime("%Y%m%d")
    rand_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"ORD-{date_str}-{rand_str}"

@app.route('/checkout', methods=['POST'])
def checkout():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    customer_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch all items from cart
    cursor.execute("""
        SELECT c.product_id, c.quantity, p.price
        FROM cart c
        JOIN products p ON c.product_id = p.id
        WHERE c.user_id = %s
    """, (customer_id,))
    cart_items = cursor.fetchall()

    if not cart_items:
        cursor.close()
        conn.close()
        flash("Your cart is empty!", "warning")
        return redirect(url_for('cart'))

    # Calculate total
    total_amount = sum(item['price'] * item['quantity'] for item in cart_items)

    # Generate unique order number
    order_number = generate_order_number()

    # Insert into orders table
    cursor.execute("""
        INSERT INTO orders (order_number, customer_id, total_amount, status, created_at)
        VALUES (%s, %s, %s, %s, %s)
    """, (order_number, customer_id, total_amount, 'Processing', datetime.now()))
    
    order_id = cursor.lastrowid

    # Insert each item into order_items table
    for item in cart_items:
        cursor.execute("""
            INSERT INTO order_items (order_id, product_id, quantity, price)
            VALUES (%s, %s, %s, %s)
        """, (order_id, item['product_id'], item['quantity'], item['price']))

    # Clear the user's cart
    cursor.execute("DELETE FROM cart WHERE user_id = %s", (customer_id,))

    conn.commit()
    cursor.close()
    conn.close()

    flash("Your order has been placed successfully!", "success")
    return redirect(url_for('order_confirmation', order_number=order_number))

@app.route('/order/confirmation/<order_number>')
def order_confirmation(order_number):
    return render_template('order_confirmation.html', order_id=order_number)


@app.route('/my-orders')
def my_orders():
    # Ensure user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # =========================
    # Fetch all orders for this user
    # =========================
    cursor.execute("""
        SELECT o.id AS order_id, o.order_number, o.total_amount, o.status, o.created_at,
               c.name AS customer_name
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        WHERE o.customer_id = %s
        ORDER BY o.created_at DESC
    """, (user_id,))
    orders = cursor.fetchall()  # ✅ must have parentheses

    if not orders:
        cursor.close()
        conn.close()
        return render_template('my_orders.html', orders=[])

    # Convert total_amount to float to avoid Decimal issues in template
    for order in orders:
        if isinstance(order.get('total_amount'), Decimal):
            order['total_amount'] = float(order['total_amount'])

    # =========================
    # Fetch all order items
    # =========================
    order_ids = [order['order_id'] for order in orders]
    if order_ids:
        placeholders = ','.join(['%s'] * len(order_ids))
        cursor.execute(f"""
            SELECT oi.order_id, oi.product_id, oi.quantity, oi.price, 
                   p.name, p.category, p.image, p.description
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id IN ({placeholders})
        """, tuple(order_ids))
        all_items = cursor.fetchall()
    else:
        all_items = []

    # Group items by order_id
    items_by_order = {}
    for item in all_items:
        order_id = item['order_id']
        items_by_order.setdefault(order_id, []).append(item)

    # =========================
    # Assign items and process each order
    # =========================
    for order in orders:
        order_items = items_by_order.get(order['order_id'], [])

        # Decode images and strings, convert price
        for item in order_items:
            if isinstance(item.get('image'), (bytes, bytearray)):
                item['image'] = item['image'].decode('utf-8')
            # fallback image if missing
            if not item.get('image'):
                item['image'] = 'default.png'

            if isinstance(item.get('price'), Decimal):
                item['price'] = float(item['price'])
            for key in ['name', 'category', 'description']:
                if isinstance(item.get(key), bytes):
                    item[key] = item[key].decode('utf-8')

        # Assign processed items to new key to avoid clash with dict.items()
        order['order_items'] = order_items

        # Format placed date
        created_at = order.get('created_at')
        if isinstance(created_at, datetime):
            order['placed_date'] = created_at.strftime("%B %d, %Y")
        else:
            order['placed_date'] = str(created_at)

        # Map status to CSS class
        order['status_class'] = {
            'Processing': 'status-processing',
            'Shipped': 'status-shipped',
            'Delivered': 'status-delivered',
            'Cancelled': 'status-cancelled'
        }.get(order.get('status'), 'status-processing')

        # Optional: add shipping_address fallback
        order['shipping_address'] = getattr(order, 'shipping_address', 'Not Provided')
        
    stats = {
        'total': len(orders),
        'processing': sum(1 for o in orders if o['status'] == 'Processing'),
        'shipped': sum(1 for o in orders if o['status'] == 'Shipped'),
        'delivered': sum(1 for o in orders if o['status'] == 'Delivered')
    }
    
    cursor.execute("""
        SELECT SUM(quantity) AS total_cart_items
        FROM cart
        WHERE user_id = %s
    """, (user_id,))
    cart_result = cursor.fetchone()
    stats['cart_items'] = int(cart_result['total_cart_items'] or 0)
    print(stats['cart_items'])

    cursor.close()
    conn.close()

    return render_template('my_orders.html', orders=orders, stats=stats)

@app.route('/track-order/<int:order_id>')
def track_order(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            o.id AS order_id,
            o.order_number,
            o.total_amount,
            o.status,
            o.created_at,
            oi.product_id,
            oi.quantity,
            oi.price,
            p.name AS product_name,
            p.image
        FROM orders o
        LEFT JOIN order_items oi ON o.id = oi.order_id
        LEFT JOIN products p ON oi.product_id = p.id
        WHERE o.id = %s AND o.customer_id = %s
    """, (order_id, user_id))

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if not rows:
        return redirect(url_for('my_orders'))

    order = {
        "order_id": rows[0]['order_id'],
        "order_number": rows[0]['order_number'],
        "total_amount": float(rows[0]['total_amount']),
        "status": rows[0]['status'],
        "created_at": rows[0]['created_at'],
        "placed_date": rows[0]['created_at'].strftime("%B %d, %Y") if isinstance(rows[0]['created_at'], datetime) else str(rows[0]['created_at']),
        "order_items": []  # <- changed key name
    }

    for row in rows:
        if row['product_id'] is not None:
            image = row['image']
            if isinstance(image, (bytes, bytearray)):
                image = image.decode('utf-8')
            if not image:
                image = 'default.png'

            order['order_items'].append({
                "product_id": row['product_id'],
                "name": row['product_name'],
                "quantity": row['quantity'],
                "price": float(row['price']),
                "image": image
            })

    return render_template('tracking.html', order=order)


@app.route('/admin/orders')
def admin_orders():
    # Admin authentication
    if session.get('role') != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch all orders
    cursor.execute("""
        SELECT o.id AS order_id, o.order_number, o.customer_id, o.total_amount, o.status, o.created_at,
               u.username AS customer_name
        FROM orders o
        LEFT JOIN users u ON o.customer_id = u.id
        ORDER BY o.created_at DESC
    """)
    orders = cursor.fetchall()

    # Fetch order items for each order
    for order in orders:
        cursor.execute("""
            SELECT oi.product_id, oi.quantity, oi.price, p.name AS product_name
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = %s
        """, (order['order_id'],))
        order['items'] = cursor.fetchall()

    cursor.close() 
    conn.close()

    return render_template('admin_orders.html', orders=orders, active_page='orders')

@app.route('/admin/products')
def admin_products():
    # Check if admin is logged in
    if session.get('role') != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch all products
    cursor.execute("""
        SELECT id, name, category, price, stock, status, description, image, rfid_tag, created_at
        FROM products
        ORDER BY created_at DESC
    """)
    products = cursor.fetchall()

    cursor.close()
    conn.close()

    # Count total products for badge
    total_products = len(products)

    return render_template('admin/products.html', products=products, total_products=total_products, active_page='products')

@app.route('/add-seller', methods=['POST'])
def add_seller():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Get form data
    name = request.form.get('sellerName')
    email = request.form.get('sellerEmail')
    password = request.form.get('sellerPassword')
    role = request.form.get('userRole')

    if not all([name, email, password, role]):
        flash("All fields are required", "danger")
        return redirect(url_for('dashboard'))

    hashed_password = generate_password_hash(password)

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, role)
            VALUES (%s, %s, %s, %s)
        """, (name, email, hashed_password, role))
        conn.commit()
        flash("Seller added successfully!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error adding seller: {str(e)}", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('admin_dashboard'))  # Back to admin page

@app.route('/seller/dashboard')
def seller_dashboard():
    if 'user_id' not in session or session.get('role') != 'seller':
        return redirect(url_for('login'))

    seller_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Seller name
    cursor.execute("""
        SELECT COALESCE(full_name, username) AS full_name
        FROM users WHERE id = %s
    """, (seller_id,))
    seller = cursor.fetchone()

    # ------------------------
    # ORDERS TABLE
    # ------------------------
    cursor.execute("""
        SELECT 
            o.id,
            o.order_number,
            o.status,
            p.name AS product_name,
            oi.quantity
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        JOIN products p ON oi.product_id = p.id
        ORDER BY o.created_at DESC
    """)
    orders = cursor.fetchall()

    # ------------------------
    # SELLER PRODUCTS TABLE
    # ------------------------
    cursor.execute("""
        SELECT 
            sp.id AS seller_product_id,
            p.name AS product_name,
            sp.stock,
            p.category,
            c.id AS customer_id,
            c.name AS customer_name,
            c.email AS customer_email,
            o.status AS order_status
        FROM seller_products sp
        JOIN products p ON sp.product_id = p.id
        LEFT JOIN order_items oi ON p.id = oi.product_id
        LEFT JOIN orders o ON oi.order_id = o.id
        LEFT JOIN customers c ON o.customer_id = c.id
        WHERE sp.seller_id = %s
        ORDER BY o.created_at DESC
    """, (seller_id,))
    seller_products = cursor.fetchall()


    cursor.close()
    conn.close()

    return render_template(
        'seller/dashboard.html',
        seller_name=seller['full_name'],
        orders=orders,
        seller_products=seller_products
    )
@app.route("/product/by_rfid/<rfid>", methods=["POST","GET"])
def get_product_by_rfid(rfid):
    if 'user_id' not in session:
        return jsonify(success=False, message="Unauthorized")

    seller_id = session['user_id']
    print("🔥 RFID:", rfid)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 1️⃣ Find processing order for this RFID
    cursor.execute("""
        SELECT 
            o.id AS order_id,
            o.order_number,
            p.id AS product_id,
            p.category,
            p.name AS product_name,
            oi.quantity
        FROM products p
        JOIN order_items oi ON p.id = oi.product_id
        JOIN orders o ON oi.order_id = o.id
        WHERE p.rfid_tag = %s
          AND o.status = 'Processing'
        LIMIT 1
    """, (rfid,))

    row = cursor.fetchone()
    print("🧾 ROW:", row)

    if not row:
        cursor.close()
        conn.close()
        return jsonify(success=False, message="No Processing order found")

    # 2️⃣ Update order status → Shipped
    cursor.execute(
        "UPDATE orders SET status = 'Shipped' WHERE id = %s",
        (row['order_id'],)
    )
    print("✅ ORDER UPDATED")

    # 3️⃣ Insert / update seller_products
    cursor.execute("""
        INSERT INTO seller_products (seller_id, product_id, stock, price, created_at)
        VALUES (%s, %s, %s, NULL, NOW())
        ON DUPLICATE KEY UPDATE
            stock = stock + VALUES(stock)
    """, (
        seller_id,
        row['product_id'],
        row['quantity']
    ))
    print("📦 INVENTORY UPDATED")

    conn.commit()
    print("💾 COMMIT DONE")

    cursor.close()
    conn.close()

    return jsonify(
        success=True,
        message=f"Order {row['order_number']} shipped & inventory updated"
    )


   

@app.route('/add-product', methods=['POST'])
def add_product_to_seller():
    if 'user_id' not in session or session.get('role') != 'seller':
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    seller_id = session['user_id']
    data = request.get_json()

    product_id = data.get('product_id')
    stock = data.get('stock', 0)
    price = data.get('price')
    order_id = data.get('order_id')  # ✅ FIX: get order_id safely
    new_status = "Processing"

    if not product_id:
        return jsonify({"success": False, "message": "Product ID is required"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Add or update seller inventory
        cursor.execute("""
            INSERT INTO seller_products (seller_id, product_id, stock, price)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                stock = VALUES(stock),
                price = VALUES(price)
        """, (seller_id, product_id, stock, price))

        # ✅ Update order status ONLY if order_id exists
        if order_id:
            cursor.execute("""
                UPDATE orders
                SET status = %s
                WHERE id = %s
            """, (new_status, order_id))

        conn.commit()

        return jsonify({
            "success": True,
            "message": "Product added to inventory and order status updated"
        })

    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()

        
@app.route('/my-inventory-data')
def my_inventory_data():
    if 'user_id' not in session or session.get('role') != 'seller':
        return jsonify({"inventory": []})

    seller_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT sp.product_id, sp.stock, sp.price, 
               p.name, p.category, p.rfid_tag, p.description
        FROM seller_products sp
        JOIN products p ON sp.product_id = p.id
        WHERE sp.seller_id = %s
    """, (seller_id,))

    inventory = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify({"inventory": inventory})

@app.route('/remove-product/<int:product_id>', methods=['DELETE'])
def remove_product(product_id):
    # Ensure user is logged in and is a seller
    if 'user_id' not in session or session.get('role') != 'seller':
        return jsonify({"error": "Unauthorized"}), 403

    seller_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Delete product from seller_products table
        cursor.execute("""
            DELETE FROM seller_products
            WHERE seller_id = %s AND product_id = %s
        """, (seller_id, product_id))

        conn.commit()

        if cursor.rowcount == 0:
            # No rows deleted → product not found or not owned by seller
            return jsonify({"message": "Product not found"}), 404

        return jsonify({"message": "Product removed successfully"}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()

@app.route('/delivery/dashboard')
def delivery_dashboard():
    # Optional: protect route (recommended)
    if 'user_id' not in session or session.get('role') != 'delivery_agent':
        return redirect(url_for('login'))

    return render_template('delivery/dashboard.html')

@app.route('/delivery/scan')
def delivery_scan():
    if 'user_id' not in session or session.get('role') != 'delivery_agent':
        return redirect(url_for('login'))

    agent_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Seller name
    cursor.execute("""
        SELECT COALESCE(full_name, username) AS full_name
        FROM users WHERE id = %s
    """, (agent_id,))
    agent = cursor.fetchone()

    # ------------------------
    # ORDERS TABLE
    # ------------------------
    cursor.execute("""
        SELECT 
            o.id,
            o.order_number,
            o.status,
            p.name AS product_name,
            oi.quantity
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        JOIN products p ON oi.product_id = p.id
        WHERE o.status = 'Shipped' OR o.status = 'Delivered'
        ORDER BY o.created_at DESC
    """)
    orders = cursor.fetchall()

    # ------------------------
    # SELLER PRODUCTS TABLE
    # ------------------------
    cursor.execute("""
        SELECT 
            dp.id AS delivery_id,
            dp.created_at AS delivered_at,
            p.id AS product_id,
            p.name AS product_name,
            p.category AS product_category,
            dp.quantity AS delivered_quantity,
            o.id AS order_id,
            o.order_number,
            o.status AS order_status,
            c.id AS customer_id,
            c.name AS customer_name,
            c.email AS customer_email
        FROM delivery_products dp
        JOIN products p ON dp.product_id = p.id
        LEFT JOIN order_items oi ON p.id = oi.product_id
        LEFT JOIN orders o ON oi.order_id = o.id
        LEFT JOIN customers c ON o.customer_id = c.id
        WHERE dp.agent_id = %s
        ORDER BY dp.created_at DESC
    """, (agent_id,))
    delivery_details = cursor.fetchall()



    cursor.close()
    conn.close()

    return render_template(
        'delivery/scan.html',
        agent_name=agent['full_name'],
        orders=orders,
        delivery_details=delivery_details
    )

@app.route("/delivery/by_rfid/<rfid>", methods=["POST"])
def get_delivery_by_rfid(rfid):
    if 'user_id' not in session:
        return jsonify(success=False, message="Unauthorized")

    agent_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 1️⃣ Fetch all shipped orders for this RFID
    cursor.execute("""
        SELECT 
            o.id AS order_id,
            o.order_number,
            p.id AS product_id,
            p.category,
            p.name AS product_name,
            oi.quantity
        FROM products p
        JOIN order_items oi ON p.id = oi.product_id
        JOIN orders o ON oi.order_id = o.id
        WHERE p.rfid_tag = %s AND o.status = 'Shipped'
        LIMIT 1
    """, (rfid,))

    rows = cursor.fetchall()

    if not rows:
        cursor.close()
        conn.close()
        return jsonify(success=False, message="No shipped orders found for this RFID")

    # 2️⃣ Loop through all orders and update them
    for row in rows:
        # Update order status → Delivered
        cursor.execute(
            "UPDATE orders SET status = 'Delivered' WHERE id = %s",
            (row['order_id'],)
        )
        # Insert delivery record
        cursor.execute("""
            INSERT INTO delivery_products (agent_id, product_id, quantity, created_at)
            VALUES (%s, %s, %s, NOW())
        """, (
            agent_id,
            row['product_id'],
            row['quantity']
        ))
        print(f"✅ Order {row['order_number']} marked Delivered")

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify(
        success=True,
        message=f"{len(rows)} order(s) delivered and inventory updated"
    )


@app.route('/add-delivery-product', methods=['POST'])
def add_product_to_delivery():
    if 'user_id' not in session or session.get('role') != 'delivery_agent':
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    seller_id = session['user_id']
    data = request.get_json()

    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)
    order_id = data.get('order_id')

    if not product_id:
        return jsonify({"success": False, "message": "Product ID is required"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Add or update delivery product
        cursor.execute("""
            INSERT INTO delivery_products (agent_id, product_id, quantity)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                quantity = quantity + VALUES(quantity)
        """, (seller_id, product_id, quantity))
        print(order_id)
        if order_id:
            cursor.execute("""
                UPDATE orders
                SET status = 'Shipped'
                WHERE id = %s
            """, (order_id,))
            
        conn.commit()

        return jsonify({
            "success": True,
            "message": "Product added to delivery"
        })

    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()

@app.route('/my-delivery-data')
def my_delivery_data():
    if 'user_id' not in session or session.get('role') != 'delivery_agent':
        return jsonify({"delivery": []})

    agent_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT dp.product_id,
               dp.quantity,
               dp.created_at,
               p.name,
               p.category,
               p.rfid_tag,
               p.description
        FROM delivery_products dp
        JOIN products p ON dp.product_id = p.id
        WHERE dp.agent_id = %s
        ORDER BY dp.created_at DESC
    """, (agent_id,))

    delivery = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify({"delivery": delivery})

@app.route('/api/get-order-status/<order_id>')
def get_order_status(order_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Matches your provided table: status, amount, created_at
    query = "SELECT status, created_at FROM orders WHERE order_number = %s"
    cursor.execute(query, (order_id,))
    order = cursor.fetchone()
    
    cursor.close()
    conn.close()

    if order:
        return jsonify({
            "success": True,
            "status": order['status'], # e.g., "Shipped"
            "placed_date": order['created_at'].isoformat()
        })
    return jsonify({"success": False, "message": "Order not found"}), 404
# ---------------- Logout ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))



if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=5050, debug=True)

