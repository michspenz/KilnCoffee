

import sqlite3
import time
import json
import os
from flask import Flask, request, render_template, redirect, url_for, session, g, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "kiln-demo-not-secure"  # fine for a local demo only

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "kiln.db")
LOG_PATH = os.path.join(BASE_DIR, "requests.log")


# ---------------------------------------------------------------------------
# Database setup + seed data
# ---------------------------------------------------------------------------

def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_db(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


def ensure_product_columns(db):
    columns = {row[1] for row in db.execute("PRAGMA table_info(products)").fetchall()}

    if "mood" not in columns:
        db.execute("ALTER TABLE products ADD COLUMN mood TEXT NOT NULL DEFAULT ''")

    if "roaster_note" not in columns:
        db.execute("ALTER TABLE products ADD COLUMN roaster_note TEXT NOT NULL DEFAULT ''")

    db.commit()

    existing_moods = {
        "Ember Reserve": "Bold",
        "Meadow Light": "Wide Awake",
        "Foundry Blend": "Unbothered",
        "Midnight Kiln": "Cozy",
        "Solstice Decaf": "No Jitters",
    }

    existing_roaster_notes = {
        "Ember Reserve": "This one was built for people who like their coffee to say something before the first sip.",
        "Meadow Light": "I roast this for the morning that needs a little more daylight.",
        "Foundry Blend": "This is the roast I keep on the grinder when I'm trying to look busy.",
        "Midnight Kiln": "The quiet one, for when the room has gone soft and the kettle feels like a ritual.",
        "Solstice Decaf": "The one I make for people who want the ceremony without the buzzy part.",
    }

    for name, mood in existing_moods.items():
        db.execute("UPDATE products SET mood = ? WHERE name = ? AND (mood IS NULL OR mood = '')", (mood, name))

    for name, roaster_note in existing_roaster_notes.items():
        db.execute(
            "UPDATE products SET roaster_note = ? WHERE name = ? AND (roaster_note IS NULL OR roaster_note = '')",
            (roaster_note, name),
        )

    db.commit()


def init_db():
    fresh = not os.path.exists(DB_PATH)
    db = sqlite3.connect(DB_PATH)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            tagline TEXT NOT NULL,
            origin TEXT NOT NULL,
            roast_level TEXT NOT NULL,
            roast_score INTEGER NOT NULL,
            price REAL NOT NULL,
            notes TEXT NOT NULL,
            accent TEXT NOT NULL,
            mood TEXT NOT NULL,
            roaster_note TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            total REAL NOT NULL,
            shipping_name TEXT NOT NULL,
            shipping_address TEXT NOT NULL,
            phone TEXT NOT NULL,
            card_last4 TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    db.commit()
    ensure_product_columns(db)

    if fresh:
        seed(db)
    db.close()


def seed(db):
    users = [
        ("sam", "coffee123", "Sam Whitfield", "sam@example.com"),
        ("alex", "coffee123", "Alex Rivera", "alex@example.com"),
    ]
    for username, pw, full_name, email in users:
        db.execute(
            "INSERT INTO users (username, password_hash, full_name, email) VALUES (?, ?, ?, ?)",
            (username, generate_password_hash(pw), full_name, email),
        )

    products = [
        ("Ember Reserve", "Slow-roasted until it remembers the fire.", "Sumatra", "Dark", 4, 18.50,
         "molasses, dark cocoa, cedar smoke", "#3F5D45", "Bold",
         "This one was built for people who like their coffee to say something before the first sip."),
        ("Meadow Light", "Bright, floral, wide awake.", "Ethiopia, Yirgacheffe", "Light", 1, 19.00,
         "jasmine, peach, wild honey", "#C48A2F", "Wide Awake",
         "I roast this for the morning that needs a little more daylight."),
        ("Foundry Blend", "The one we drink while roasting the rest.", "House Blend", "Medium", 2, 16.00,
         "toffee, walnut, orange peel", "#A65A2E", "Unbothered",
         "This is the roast I keep on the grinder when I'm trying to look busy."),
        ("Midnight Kiln", "Roasted past the point of politeness.", "Guatemala", "Extra Dark", 5, 17.50,
         "bittersweet chocolate, roasted almond", "#2B1E14", "Cozy",
         "The quiet one, for when the room has gone soft and the kettle feels like a ritual."),
        ("Solstice Decaf", "All the ritual, none of the jitters.", "Colombia", "Medium", 2, 17.00,
         "caramel, red apple, brown sugar", "#7A6A4F", "No Jitters",
         "The one I make for people who want the ceremony without the buzzy part."),
    ]
    for p in products:
        db.execute(
            "INSERT INTO products (name, tagline, origin, roast_level, roast_score, price, notes, accent, mood, roaster_note) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            p,
        )
    db.commit()

    # Seed orders so the IDOR has real neighboring data to "steal"
    orders = [
        (1, 1, 2, 37.00, "Sam Whitfield", "14 Marlow Street, Lagos", "+234 801 555 0142", "4242", "Roasting", "2026-07-10 09:12:00"),
        (2, 2, 1, 19.00, "Alex Rivera", "88 Rivergate Ave, Lagos", "+234 802 555 0198", "1881", "Shipped", "2026-07-11 14:03:00"),
        (1, 3, 1, 16.00, "Sam Whitfield", "14 Marlow Street, Lagos", "+234 801 555 0142", "4242", "Delivered", "2026-07-05 08:44:00"),
        (2, 4, 3, 52.50, "Alex Rivera", "88 Rivergate Ave, Lagos", "+234 802 555 0198", "1881", "Roasting", "2026-07-12 11:20:00"),
    ]
    for o in orders:
        db.execute(
            "INSERT INTO orders (user_id, product_id, quantity, total, shipping_name, shipping_address, "
            "phone, card_last4, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            o,
        )
    db.commit()


# ---------------------------------------------------------------------------
# Logging middleware — every request, one JSON line, for the blue-team side
# ---------------------------------------------------------------------------

SENSITIVE_FIELDS = {"password", "confirm_password"}


@app.before_request
def log_request():
    form_data = {k: v for k, v in request.form.to_dict().items() if k not in SENSITIVE_FIELDS}
    entry = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "ip": request.remote_addr,
        "method": request.method,
        "path": request.path,
        "user_agent": request.headers.get("User-Agent", ""),
        "session_user_id": session.get("user_id"),
        "session_username": session.get("username"),
        "form_data": form_data,
    }
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def current_user():
    if "user_id" not in session:
        return None
    db = get_db()
    return db.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()


@app.context_processor
def inject_user():
    return {"current_user": current_user()}


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()

        db = get_db()
        existing = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            flash("That username is already taken.", "error")
            return render_template("register.html")

        db.execute(
            "INSERT INTO users (username, password_hash, full_name, email) VALUES (?, ?, ?, ?)",
            (username, generate_password_hash(password), full_name, email),
        )
        db.commit()
        flash("Account created — log in to continue.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash(f"Welcome back, {user['full_name']}.", "success")
            return redirect(url_for("index"))
        flash("Invalid username or password.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You've been logged out.", "success")
    return redirect(url_for("index"))


def require_login():
    if "user_id" not in session:
        flash("Please log in first.", "error")
        return redirect(url_for("login"))
    return None


# ---------------------------------------------------------------------------
# Storefront
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    db = get_db()
    products = db.execute("SELECT * FROM products ORDER BY id").fetchall()
    return render_template("index.html", products=products)


@app.route("/product/<int:product_id>")
def product_detail(product_id):
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if not product:
        flash("That product doesn't exist.", "error")
        return redirect(url_for("index"))
    return render_template("product.html", product=product)


@app.route("/order/create", methods=["POST"])
def order_create():
    redirect_resp = require_login()
    if redirect_resp:
        return redirect_resp

    product_id = request.form.get("product_id", type=int)
    quantity = request.form.get("quantity", default=1, type=int)
    shipping_address = request.form.get("shipping_address", "").strip()
    phone = request.form.get("phone", "").strip()
    card_last4 = request.form.get("card_last4", "0000").strip()[-4:]

    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if not product:
        flash("That product doesn't exist.", "error")
        return redirect(url_for("index"))

    user = current_user()
    total = round(product["price"] * quantity, 2)

    cur = db.execute(
        "INSERT INTO orders (user_id, product_id, quantity, total, shipping_name, shipping_address, "
        "phone, card_last4, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            session["user_id"], product_id, quantity, total, user["full_name"], shipping_address,
            phone, card_last4, "Roasting", time.strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    db.commit()
    new_order_id = cur.lastrowid
    flash("Order placed! Your beans are going in the kiln.", "success")
    return redirect(url_for("order_detail", order_id=new_order_id))


@app.route("/orders")
def my_orders():
    redirect_resp = require_login()
    if redirect_resp:
        return redirect_resp

    db = get_db()
    # NOTE: this list view IS correctly scoped to the logged-in user.
    # That's realistic — the bug isn't here, it's one click away.
    rows = db.execute(
        """
        SELECT orders.*, products.name AS product_name, products.accent AS accent
        FROM orders JOIN products ON orders.product_id = products.id
        WHERE orders.user_id = ?
        ORDER BY orders.id DESC
        """,
        (session["user_id"],),
    ).fetchall()
    return render_template("my_orders.html", orders=rows)


@app.route("/order/<int:order_id>")
def order_detail(order_id):
    redirect_resp = require_login()
    if redirect_resp:
        return redirect_resp

    db = get_db()
    # VULNERABLE: fetches ANY order by ID with no check that
    # order["user_id"] == session["user_id"]. Change the number in the
    # URL and you're looking at someone else's shipping address, phone
    # number, and card digits.
    order = db.execute(
        """
        SELECT orders.*, products.name AS product_name, products.accent AS accent
        FROM orders JOIN products ON orders.product_id = products.id
        WHERE orders.id = ?
        """,
        (order_id,),
    ).fetchone()

    if not order:
        flash("That order doesn't exist.", "error")
        return redirect(url_for("my_orders"))

    return render_template("order.html", order=order)


@app.route("/order/<int:order_id>/update", methods=["POST"])
def order_update(order_id):
    redirect_resp = require_login()
    if redirect_resp:
        return redirect_resp

    new_address = request.form.get("shipping_address", "").strip()
    db = get_db()
    # VULNERABLE: same missing ownership check, but this time it's a WRITE —
    # any logged-in user can edit any order's shipping address.
    db.execute("UPDATE orders SET shipping_address = ? WHERE id = ?", (new_address, order_id))
    db.commit()
    flash("Shipping address updated.", "success")
    return redirect(url_for("order_detail", order_id=order_id))


@app.route("/order/<int:order_id>/cancel", methods=["POST"])
def order_cancel(order_id):
    redirect_resp = require_login()
    if redirect_resp:
        return redirect_resp

    db = get_db()
    # VULNERABLE: same missing ownership check — any logged-in user can
    # cancel any order.
    db.execute("UPDATE orders SET status = ? WHERE id = ?", ("Cancelled", order_id))
    db.commit()
    flash("Order cancelled.", "success")
    return redirect(url_for("order_detail", order_id=order_id))


@app.route("/account", methods=["GET"])
def account():
    redirect_resp = require_login()
    if redirect_resp:
        return redirect_resp
    return render_template("account.html")


@app.route("/account/report", methods=["POST"])
def account_report():
    redirect_resp = require_login()
    if redirect_resp:
        return redirect_resp

    message = request.form.get("message", "").strip()
    db = get_db()
    db.execute(
        "INSERT INTO reports (user_id, message, created_at) VALUES (?, ?, ?)",
        (session["user_id"], message, time.strftime("%Y-%m-%d %H:%M:%S")),
    )
    db.commit()
    flash("Thanks — our security team has been notified and will investigate.", "success")
    return redirect(url_for("account"))


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
