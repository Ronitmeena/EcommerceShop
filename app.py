\
import os, json
from datetime import datetime
from urllib.parse import urlencode

from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY","dev-secret-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL","sqlite:///app.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# ------------------ Models ------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=True)
    category = db.relationship(Category, backref="products")

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    items_json = db.Column(db.Text, nullable=False)  # list of {product_id, title, qty, price}
    total = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ------------------ Helpers ------------------
def get_cart():
    return session.setdefault("cart", {})  # {product_id: qty}

def cart_items():
    c = get_cart()
    ids = [int(pid) for pid in c.keys()]
    products = Product.query.filter(Product.id.in_(ids)).all() if ids else []
    by_id = {p.id: p for p in products}
    items = []
    total = 0.0
    for pid, qty in c.items():
        p = by_id.get(int(pid))
        if not p: 
            continue
        line_total = p.price * qty
        total += line_total
        items.append({"product": p, "qty": qty, "line_total": line_total})
    return items, total

@app.context_processor
def inject_cart_count():
    cart = get_cart()
    return {"cart_count": sum(cart.values())}

# ------------------ Routes ------------------
@app.route("/")
def index():
    q = request.args.get("q","").strip()
    cat_id = request.args.get("category","")
    categories = Category.query.order_by(Category.name).all()
    products = Product.query
    if q:
        like = f"%{q.lower()}%"
        products = products.filter(db.or_(db.func.lower(Product.title).like(like),
                                          db.func.lower(Product.description).like(like)))
    if cat_id:
        products = products.filter_by(category_id=cat_id)
    products = products.order_by(Product.id.desc()).all()
    return render_template("index.html", products=products, categories=categories, q=q, cat_id=str(cat_id))

@app.route("/product/<int:pid>")
def product_detail(pid):
    p = Product.query.get_or_404(pid)
    return render_template("product_detail.html", p=p)

@app.route("/add-to-cart/<int:pid>", methods=["POST"])
def add_to_cart(pid):
    qty = int(request.form.get("qty", 1))
    product = Product.query.get_or_404(pid)
    cart = get_cart()
    cart[str(pid)] = cart.get(str(pid), 0) + max(1, qty)
    session.modified = True
    flash(f"Added {product.title} (x{qty}) to cart.", "success")
    return redirect(request.referrer or url_for("index"))

@app.route("/cart", methods=["GET","POST"])
def cart_view():
    if request.method == "POST":
        # update quantities or remove
        action = request.form.get("action")
        pid = request.form.get("pid")
        cart = get_cart()
        if action == "update":
            qty = max(0, int(request.form.get("qty", 1)))
            if qty == 0:
                cart.pop(pid, None)
            else:
                cart[pid] = qty
        elif action == "clear":
            session["cart"] = {}
        session.modified = True
    items, total = cart_items()
    return render_template("cart.html", items=items, total=total)

@app.route("/checkout", methods=["GET","POST"])
def checkout():
    items, total = cart_items()
    if request.method == "POST":
        if not items:
            flash("Your cart is empty.", "warning")
            return redirect(url_for("index"))
        order_items = [{
            "product_id": it["product"].id,
            "title": it["product"].title,
            "qty": it["qty"],
            "price": it["product"].price
        } for it in items]
        order = Order(user_id=current_user.id if current_user.is_authenticated else None,
                      items_json=json.dumps(order_items),
                      total=total)
        db.session.add(order)
        db.session.commit()
        session["cart"] = {}
        flash(f"Order #{order.id} placed successfully!", "success")
        return redirect(url_for("index"))
    return render_template("checkout.html", items=items, total=total)

# ------------- Auth -------------
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].lower().strip()
        password = request.form["password"]
        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "warning")
            return redirect(url_for("register"))
        user = User(name=name, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Registration successful. Please login.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].lower().strip()
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash("Welcome back!", "success")
            next_url = request.args.get("next")
            return redirect(next_url or url_for("index"))
        flash("Invalid credentials.", "danger")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("index"))

# ------------- CLI Utilities -------------
@app.cli.command("init-db")
def init_db():
    """Initialize database tables."""
    db.create_all()
    print("Initialized the database.")

@app.cli.command("seed")
def seed():
    """Seed sample categories and products."""
    if not Category.query.first():
        categories = ["Electronics", "Clothing", "Books", "Home"]
        cats = [Category(name=c) for c in categories]
        db.session.add_all(cats); db.session.commit()
    else:
        cats = Category.query.all()
    if not Product.query.first():
        import random
        sample = [
            ("Wireless Headphones", "Comfortable over‑ear headphones with clear sound.", 1999.0, "https://picsum.photos/seed/headphones/600/400", "Electronics"),
            ("Smart Watch", "Track fitness, notifications, and heart rate.", 3499.0, "https://picsum.photos/seed/smartwatch/600/400", "Electronics"),
            ("Cotton T‑Shirt", "Soft, breathable cotton tee in multiple colors.", 499.0, "https://picsum.photos/seed/tshirt/600/400", "Clothing"),
            ("Stainless Water Bottle", "Insulated bottle keeps drinks cold for 24h.", 699.0, "https://picsum.photos/seed/bottle/600/400", "Home"),
            ("Programming Book", "Master Python with practical examples.", 899.0, "https://picsum.photos/seed/book/600/400", "Books"),
        ]
        cat_by_name = {c.name: c for c in cats}
        for title, desc, price, img, cname in sample:
            db.session.add(Product(
                title=title, description=desc, price=price, image_url=img, category=cat_by_name[cname]
            ))
        db.session.commit()
    print("Seeded data.")
    
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
