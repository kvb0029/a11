from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
import random
import datetime

# Initialize Flask app and database
app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ecommerce.db'
db = SQLAlchemy(app)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

# Product model
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)
    stock = db.Column(db.Integer, nullable=False)

# Order model
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    products = db.Column(db.Text, nullable=False)  # JSON string of product IDs and quantities
    total_price = db.Column(db.Float, nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.datetime.now)

# Cart model
class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

@app.route('/')
def home():
    products = Product.query.all()
    return render_template('home.html', products=products)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash("Username already exists!")
        else:
            new_user = User(username=username, password=password)
            db.session.add(new_user)
            db.session.commit()
            flash("Registration successful!")
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            return redirect(url_for('home'))
        else:
            flash("Invalid credentials!")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully!")
    return redirect(url_for('home'))

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'user_id' not in session:
        flash("Please log in to add items to your cart.")
        return redirect(url_for('login'))
    quantity = int(request.form['quantity'])
    product = Product.query.get(product_id)
    if product.stock < quantity:
        flash("Not enough stock available!")
        return redirect(url_for('home'))
    cart_item = Cart.query.filter_by(user_id=session['user_id'], product_id=product_id).first()
    if cart_item:
        cart_item.quantity += quantity
    else:
        new_item = Cart(user_id=session['user_id'], product_id=product_id, quantity=quantity)
        db.session.add(new_item)
    product.stock -= quantity
    db.session.commit()
    flash("Item added to cart!")
    return redirect(url_for('home'))

@app.route('/cart')
def view_cart():
    if 'user_id' not in session:
        flash("Please log in to view your cart.")
        return redirect(url_for('login'))
    cart_items = Cart.query.filter_by(user_id=session['user_id']).all()
    total = sum(item.product.price * item.quantity for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/checkout', methods=['POST'])
def checkout():
    if 'user_id' not in session:
        flash("Please log in to proceed with checkout.")
        return redirect(url_for('login'))
    cart_items = Cart.query.filter_by(user_id=session['user_id']).all()
    if not cart_items:
        flash("Your cart is empty!")
        return redirect(url_for('home'))
    total_price = sum(item.product.price * item.quantity for item in cart_items)
    order = Order(user_id=session['user_id'], products=str([(item.product_id, item.quantity) for item in cart_items]), total_price=total_price)
    db.session.add(order)
    for item in cart_items:
        db.session.delete(item)
    db.session.commit()
    flash("Order placed successfully!")
    return redirect(url_for('order_history'))

@app.route('/order_history')
def order_history():
    if 'user_id' not in session:
        flash("Please log in to view your order history.")
        return redirect(url_for('login'))
    orders = Order.query.filter_by(user_id=session['user_id']).all()
    return render_template('order_history.html', orders=orders)

@app.route('/admin')
def admin_dashboard():
    if not session.get('is_admin'):
        flash("Unauthorized access!")
        return redirect(url_for('home'))
    users = User.query.all()
    products = Product.query.all()
    orders = Order.query.all()
    return render_template('admin_dashboard.html', users=users, products=products, orders=orders)

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if not session.get('is_admin'):
        flash("Unauthorized access!")
        return redirect(url_for('home'))
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        description = request.form['description']
        stock = int(request.form['stock'])
        new_product = Product(name=name, price=price, description=description, stock=stock)
        db.session.add(new_product)
        db.session.commit()
        flash("Product added successfully!")
        return redirect(url_for('admin_dashboard'))
    return render_template('add_product.html')

@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    if not session.get('is_admin'):
        flash("Unauthorized access!")
        return redirect(url_for('home'))
    product = Product.query.get(product_id)
    if product:
        db.session.delete(product)
        db.session.commit()
        flash("Product deleted successfully!")
    else:
        flash("Product not found!")
    return redirect(url_for('admin_dashboard'))

@app.route('/update_stock/<int:product_id>', methods=['POST'])
def update_stock(product_id):
    if not session.get('is_admin'):
        flash("Unauthorized access!")
        return redirect(url_for('home'))
    product = Product.query.get(product_id)
    if product:
        new_stock = int(request.form['stock'])
        product.stock = new_stock
        db.session.commit()
        flash("Stock updated successfully!")
    else:
        flash("Product not found!")
    return redirect(url_for('admin_dashboard'))

@app.route('/calculate_discount/<int:product_id>', methods=['POST'])
def calculate_discount(product_price, discount_rate):
    """Calculate the discounted price."""
    discounted_price = product_price - (product_price * discount_rate / 100)
    return max(discounted_price, 0)  # Ensure price is not negative

@app.route('/send_email/<int:product_id>', methods=['POST'])
def send_email(email_address, subject, body):
    """Simulate sending an email."""
    print(f"Sending email to {email_address} with subject '{subject}' and body: {body}")

@app.route('/generate_promo_code/<int:product_id>', methods=['POST'])
def generate_promo_code():
    """Generate a random promotional code."""
    promo_code = f"PROMO{random.randint(1000, 9999)}"
    return promo_code

@app.route('/log_user_action/<int:product_id>', methods=['POST'])
def log_user_action(user_id, action):
    """Log the actions performed by the user."""
    print(f"User {user_id} performed the action: {action}")

@app.route('/recommend_products/<int:product_id>', methods=['POST'])
def recommend_products(user_id):
    """Recommend products for the user."""
    recommendations = ["Product A", "Product B", "Product C"]
    print(f"Recommended products for User {user_id}: {', '.join(recommendations)}")

@app.route('/format_price/<int:product_id>', methods=['POST'])
def format_price(price):
    """Format the price to include a currency symbol."""
    return f"${price:.2f}"

@app.route('/validate_input/<int:product_id>', methods=['POST'])
def validate_input(input_data):
    """Validate the user's input."""
    if not input_data:
        return "Input cannot be empty."
    if len(input_data) > 100:
        return "Input is too long."
    return "Input is valid."

@app.route('/calculate_delivery_date/<int:product_id>', methods=['POST'])
def calculate_delivery_date():
    """Calculate an estimated delivery date."""
    delivery_date = datetime.datetime.now() + datetime.timedelta(days=random.randint(1, 7))
    return delivery_date.strftime("%Y-%m-%d")

@app.route('/track_inventory/<int:product_id>', methods=['POST'])
def track_inventory(product_id):
    """Track inventory for a given product."""
    inventory_status = random.choice(["In Stock", "Low Stock", "Out of Stock"])
    print(f"Product {product_id} inventory status: {inventory_status}")

@app.route('/apply_coupon/<int:product_id>', methods=['POST'])
def apply_coupon(cart_total, coupon_code):
    """Apply a coupon and calculate the discounted total."""
    discount = random.randint(5, 20) if coupon_code else 0
    new_total = cart_total - (cart_total * discount / 100)
    return max(new_total, 0)  # Ensure total is not negative

@app.route('/calculate_shipping/<int:product_id>', methods=['POST'])
def calculate_shipping(address):
    """Calculate shipping charges based on the address."""
    base_rate = 5.0
    extra_charges = random.randint(0, 10)  # Random extra charges
    total_shipping = base_rate + extra_charges
    print(f"Shipping charges for address {address}: ${total_shipping:.2f}")
    return total_shipping

@app.route('/generate_user_report/<int:product_id>', methods=['POST'])
def generate_user_report(user_id):
    """Generate a summary report for the user."""
    report = {
        "user_id": user_id,
        "total_orders": random.randint(1, 50),
        "total_spent": round(random.uniform(100, 10000), 2),
        "loyalty_points": random.randint(0, 1000)
    }
    print(f"Report for User {user_id}: {report}")
    return report

@app.route('/log_error/<int:product_id>', methods=['POST'])
def log_error(error_message):
    """Log an error message for debugging purposes."""
    error_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[ERROR] {error_time} - {error_message}")

def calculate_user_loyalty_points(user_id, purchase_amount):
    """Calculate loyalty points based on the purchase amount."""
    points = int(purchase_amount // 10)  # 1 point for every $10 spent
    print(f"User {user_id} earned {points} loyalty points.")
    return points

@app.route('/verify_coupon/<int:product_id>', methods=['POST'])
def verify_coupon(coupon_code):
    """Check if a coupon code is valid."""
    valid_coupons = ["SAVE10", "FREESHIP", "DISCOUNT20"]
    is_valid = coupon_code in valid_coupons
    print(f"Coupon '{coupon_code}' validity: {is_valid}")
    return is_valid

@app.route('/calculate_tax/<int:product_id>', methods=['POST'])
def calculate_tax(cart_total):
    """Calculate tax based on the total amount."""
    tax_rate = 0.07  # 7% tax
    tax = cart_total * tax_rate
    print(f"Tax for cart total {cart_total}: ${tax:.2f}")
    return tax

@app.route('/restock_inventory/<int:product_id>', methods=['POST'])
def restock_inventory(product_id, quantity):
    """Restock the inventory for a specific product."""
    print(f"Restocking Product {product_id} with {quantity} units.")
    return True

@app.route('/add_to_wishlist/<int:product_id>', methods=['POST'])
def add_to_wishlist(user_id, product_id):
    """Add a product to the user's wishlist."""
    print(f"User {user_id} added Product {product_id} to their wishlist.")
    return True

@app.route('/generate_order_id/<int:product_id>', methods=['POST'])
def generate_order_id():
    """Generate a random order ID."""
    order_id = f"ORD-{random.randint(10000, 99999)}"
    print(f"Generated Order ID: {order_id}")
    return order_id

@app.route('/calculate_delivery_time/<int:product_id>', methods=['POST'])
def calculate_delivery_time(product_id):
    """Calculate estimated delivery time based on product availability."""
    delivery_time = random.randint(2, 7)  # Random delivery time in days
    print(f"Estimated delivery time for Product {product_id}: {delivery_time} days")
    return delivery_time

@app.route('/get_product_rating/<int:product_id>', methods=['POST'])
def get_product_rating(product_id):
    """Fetch a random rating for a product."""
    rating = round(random.uniform(3.0, 5.0), 1)  # Random rating between 3.0 and 5.0
    print(f"Product {product_id} has a rating of {rating} stars.")
    return rating

@app.route('/process_refund/<int:product_id>', methods=['POST'])
def process_refund(order_id, reason):
    """Process a refund for an order."""
    print(f"Refund initiated for Order {order_id} due to reason: {reason}")
    return True

@app.route('/generate_tracking_id/<int:product_id>', methods=['POST'])
def generate_tracking_id(order_id):
    """Generate a random tracking ID for an order."""
    tracking_id = f"TRACK-{order_id}-{random.randint(1000, 9999)}"
    print(f"Generated tracking ID: {tracking_id}")
    return tracking_id

@app.route('/detect_fraudulent_activity/<int:product_id>', methods=['POST'])
def detect_fraudulent_activity(user_id):
    """Detect suspicious activities in a user's account."""
    suspicious = random.choice([True, False])
    if suspicious:
        print(f"Suspicious activity detected in User {user_id}'s account.")
    else:
        print(f"No suspicious activity detected for User {user_id}.")
    return suspicious

@app.route('/calculate_tax/<int:product_id>', methods=['POST'])
def calculate_tax(total_price, tax_rate=7.5):
    """Calculate estimated tax based on the total price."""
    tax = total_price * (tax_rate / 100)
    print(f"Calculated tax for ${total_price:.2f}: ${tax:.2f}")
    return tax

@app.route('/send_sms/<int:product_id>', methods=['POST'])
def send_sms(phone_number, message):
    """Simulate sending an SMS notification."""
    print(f"Sending SMS to {phone_number}: {message}")

@app.route('/fetch_user_reviews/<int:product_id>', methods=['POST'])
def fetch_user_reviews(product_id):
    """Fetch random reviews for a product."""
    reviews = [
        "Great product! Highly recommend.",
        "Not bad, but could be better.",
        "Terrible quality. Do not buy.",
        "Excellent value for money!",
        "Will definitely purchase again."
    ]
    selected_reviews = random.sample(reviews, random.randint(1, 3))
    print(f"Reviews for Product {product_id}: {selected_reviews}")
    return selected_reviews

@app.route('/add_to_whishlist/<int:product_id>', methods=['POST'])
def add_to_wishlist(user_id, product_id):
    """Add a product to the user's wishlist."""
    print(f"User {user_id} added Product {product_id} to their wishlist.")
    return True

@app.route('/calculate_shipping_cost/<int:product_id>', methods=['POST'])
def calculate_shipping_cost(distance_km, weight_kg):
    """Calculate shipping cost based on distance and weight."""
    base_cost = 5.0  # Base cost in dollars
    cost = base_cost + (0.5 * distance_km) + (0.2 * weight_kg)
    print(f"Calculated shipping cost: ${cost:.2f} for {distance_km}km and {weight_kg}kg.")
    return cost


if __name__ == '__main__':
    # db.create_all()
    app.run(debug=True)
