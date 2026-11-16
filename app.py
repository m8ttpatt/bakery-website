r"""
BACKEND — the "server" half of the website.

When someone visits your site, their browser sends a *request* to this program.
This program decides what to send back: an HTML page, or raw data (JSON).

Run it with:   .venv\Scripts\python.exe app.py
Then open:     http://127.0.0.1:5000          (the shop)
               http://127.0.0.1:5000/admin    (your private dashboard)
"""

import json
import math
import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import date
from functools import wraps
from pathlib import Path

from flask import (Flask, abort, flash, jsonify, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "bakery.db"
COOKIE_PHOTO_DIR = BASE_DIR / "static" / "images" / "cookies"
PHOTO_TYPES = (".jpg", ".jpeg", ".png", ".webp")

# The "private" folder holds secrets and customer data. The website never serves it,
# and .gitignore keeps it out of Git, so it never ends up on GitHub.
PRIVATE_DIR = BASE_DIR / "private"
PRIVATE_DIR.mkdir(exist_ok=True)
PASSWORD_FILE = PRIVATE_DIR / "admin_password_hash.txt"
SECRET_KEY_FILE = PRIVATE_DIR / "secret_key.txt"
PAST_ORDERS_FILE = PRIVATE_DIR / "past_orders.json"


# ---------------------------------------------------------------------------
# BUSINESS RULES — edit these to change prices, sizes, or the featured flavor.
# ---------------------------------------------------------------------------

PICKUP_LOCATION = "New York"

# The flavor shown big on the home page. Change it each season.
FEATURED_FLAVOR = "Cookie Butter Stuffed Biscoff"
FEATURED_LABEL = "New fall flavor"

# Cookie packs (~4-inch cookies). 12 and 18 packs can be split evenly between 2 flavors.
PACK_SIZES = {
    6: {"price": 26.00, "max_flavors": 1},
    12: {"price": 48.00, "max_flavors": 2},
    18: {"price": 70.00, "max_flavors": 2},
}
MAX_PACKS_PER_LINE = 10
# Above this many pack cookies, the basket suggests catering (it doesn't block the order).
CATERING_HINT_AT = 24

# Catering trays (~3-inch cookies): the only tray sizes customers can pick.
CATERING_SIZES = [24, 48, 72, 96]
CATERING_STEP = 6  # each flavor is chosen in sets of 6

# (name, description, pack price per cookie, catering price per cookie). None = not offered.
MENU = [
    ("Brown Butter Chocolate Chip",
     "A nutty brown butter classic meets rich chopped chocolate, creating a warm, indulgent "
     "treat with a perfect balance of sweet and savory.", 4.50, 3.75),
    ("Red Velvet Cheesecake",
     "A soft red velvet base filled with creamy cream cheese and chocolate chips, drizzled "
     "with white chocolate for a decadent finish.", 5.00, 3.75),
    ("Cookie Butter Stuffed Biscoff",
     "Buttery Biscoff cookie dough stuffed with gooey cookie butter and Biscoff cookie bits, "
     "with white and dark chocolate chips.", 5.00, 3.75),
    ("S'mores",
     "A smoky chocolate chip cookie with graham crackers and a toasted marshmallow on top: "
     "a campfire classic in every bite.", 5.00, 3.75),
    ("Cookie Monster",
     "Packed with Oreos, Chips Ahoy, and white & dark chocolate chips, this fun, stuffed "
     "cookie is topped with white chocolate eyeballs.", 5.00, 3.75),
    ("Brookie",
     "A rich, fudgy brownie in cookie form: chewy, dense, and packed with chocolate flavor.",
     4.50, 3.75),
    ("Birthday Cake",
     "A cake batter base with sprinkles and golden Oreos, topped with creamy frosting for a "
     "festive, sweet treat.", 5.00, 3.75),
    ("Cookies n' Cream",
     "A rich, fudgy Oreo cookie base packed with creamy white chocolate chips, finished with "
     "a drizzle of melted white chocolate.", 5.00, 3.75),
]


# ---------------------------------------------------------------------------
# APP SETUP
# ---------------------------------------------------------------------------

app = Flask(__name__)

# The secret key signs your login cookie so nobody can fake being logged in.
if not SECRET_KEY_FILE.exists():
    SECRET_KEY_FILE.write_text(secrets.token_hex(32))
app.secret_key = SECRET_KEY_FILE.read_text().strip()
# Stops other websites from secretly submitting forms to your admin page.
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


@app.template_filter("money")
def money(value):
    """Lets templates write {{ 48|money }} and get $48.00."""
    return f"${value or 0:,.2f}"


@app.context_processor
def shared_template_values():
    """Values every page template can use."""
    return {"pickup_location": PICKUP_LOCATION}


# ---------------------------------------------------------------------------
# DATABASE
# ---------------------------------------------------------------------------

@contextmanager
def db():
    """Open the database, save changes when done, and always close it."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name: row["total"]
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create the tables the first time, then fill in the menu and your past orders."""
    with db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS products (
                id             INTEGER PRIMARY KEY,
                name           TEXT NOT NULL,
                description    TEXT,
                personal_price REAL,          -- NULL = not sold in packs
                event_price    REAL           -- NULL = not offered for catering
            );
            CREATE TABLE IF NOT EXISTS orders (
                id           INTEGER PRIMARY KEY,
                customer     TEXT NOT NULL,
                contact      TEXT,
                order_type   TEXT NOT NULL,   -- 'personal', 'catering', 'mixed', 'event' or 'manual'
                items        TEXT NOT NULL,   -- e.g. "2 × 6-pack S'mores"
                cookie_count INTEGER,
                total        REAL NOT NULL,
                order_date   TEXT,
                due_date     TEXT,
                status       TEXT NOT NULL DEFAULT 'unpaid',   -- 'unpaid' or 'paid'
                payment_info TEXT,
                notes        TEXT,
                created_at   TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS expenses (
                id            INTEGER PRIMARY KEY,
                purchase_date TEXT NOT NULL,
                item          TEXT NOT NULL,
                amount        REAL NOT NULL,
                notes         TEXT,
                created_at    TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS reviews (
                id         INTEGER PRIMARY KEY,
                author     TEXT NOT NULL,     -- e.g. "@cookiefan22" or "Ms. Eva"
                text       TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)
        if conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO products (name, description, personal_price, event_price) VALUES (?, ?, ?, ?)",
                MENU,
            )
        # Import orders from your old order sheet (stored privately) into an empty database.
        if conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0 and PAST_ORDERS_FILE.exists():
            past_orders = json.loads(PAST_ORDERS_FILE.read_text(encoding="utf-8"))
            conn.executemany(
                "INSERT INTO orders (customer, contact, order_type, items, cookie_count, total, "
                "order_date, due_date, status, payment_info, notes) VALUES (:customer, :contact, "
                ":order_type, :items, :cookie_count, :total, :order_date, :due_date, :status, "
                ":payment_info, :notes)",
                past_orders,
            )


# ---------------------------------------------------------------------------
# PHOTOS — drop files into static/images/cookies/ named after the flavor:
#   cookie-butter-stuffed-biscoff.jpg        (main photo)
#   cookie-butter-stuffed-biscoff-hover.jpg  (shown when the mouse hovers)
# ---------------------------------------------------------------------------

def slugify(name):
    """'S'mores' -> 's-mores'. Turns a flavor name into a safe file name."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def find_photo(stem):
    for ext in PHOTO_TYPES:
        if (COOKIE_PHOTO_DIR / f"{stem}{ext}").exists():
            return url_for("static", filename=f"images/cookies/{stem}{ext}")
    return None


def with_photos(row):
    """Turn a database row into a dict that also knows its photo URLs (or None)."""
    product = dict(row)
    product["slug"] = slugify(product["name"])
    product["image"] = find_photo(product["slug"])
    product["hover_image"] = find_photo(product["slug"] + "-hover")
    return product


def load_products(only=None):
    """All products, or only those sold in 'packs' or for 'catering'."""
    with db() as conn:
        rows = conn.execute("SELECT * FROM products ORDER BY id").fetchall()
    products = [with_photos(r) for r in rows]
    if only == "packs":
        products = [p for p in products if p["personal_price"] is not None]
    elif only == "catering":
        products = [p for p in products if p["event_price"] is not None]
    return products


# ---------------------------------------------------------------------------
# PRICING — the server always calculates the price itself. Never trust a price
# sent by the browser: anyone can edit what their browser sends.
# ---------------------------------------------------------------------------

def to_int(value, message):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(message)


def price_basket(items, products):
    """Check every basket item and return (items text, cookie count, total, order type).
    Raises ValueError with a customer-friendly message if anything is wrong."""
    if not isinstance(items, list) or not items:
        raise ValueError("Your basket is empty.")
    if len(items) > 30:
        raise ValueError("That's a big order! Please message us directly.")

    lines, count, total, kinds = [], 0, 0.0, set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Something in your basket isn't valid.")

        if item.get("type") == "pack":
            size = to_int(item.get("size"), "Unknown pack size.")
            qty = to_int(item.get("qty"), "Unknown quantity.")
            if size not in PACK_SIZES:
                raise ValueError("Packs come in " + ", ".join(map(str, PACK_SIZES)) + " cookies.")
            if not 1 <= qty <= MAX_PACKS_PER_LINE:
                raise ValueError(f"You can order 1 to {MAX_PACKS_PER_LINE} of each pack.")

            raw_flavors = item.get("flavors")
            if raw_flavors is None:  # older baskets: product_id + optional second_id
                raw_flavors = [item.get("product_id")] + ([item["second_id"]] if item.get("second_id") else [])
            if not isinstance(raw_flavors, list) or not raw_flavors:
                raise ValueError("Please choose a flavor.")
            flavor_ids = [to_int(f, "Unknown cookie.") for f in raw_flavors]
            if len(set(flavor_ids)) != len(flavor_ids):
                raise ValueError("Pick two different flavors for a half-and-half pack.")
            if len(flavor_ids) > PACK_SIZES[size]["max_flavors"]:
                raise ValueError(f"The {size}-cookie pack is one flavor only.")
            for fid in flavor_ids:
                if fid not in products or products[fid]["personal_price"] is None:
                    raise ValueError("One of those cookies isn't sold in packs.")

            each = size // len(flavor_ids)  # half and half: 6 + 6 or 9 + 9
            contents = " + ".join(f"{each} {products[fid]['name']}" for fid in flavor_ids)
            lines.append(f"{qty} × {size}-pack ({contents})")
            count += size * qty
            total += PACK_SIZES[size]["price"] * qty
            kinds.add("personal")

        elif item.get("type") == "catering":
            size = to_int(item.get("size"), "Unknown tray size.")
            flavors = item.get("flavors")
            if size not in CATERING_SIZES:
                raise ValueError("Catering trays come in " + ", ".join(map(str, CATERING_SIZES)) + " cookies.")
            if not isinstance(flavors, dict):
                raise ValueError("Please choose flavors for your catering tray.")
            parts, tray_count = [], 0
            for raw_id, raw_n in flavors.items():
                n = to_int(raw_n, f"Flavors come in sets of {CATERING_STEP}.")
                if n == 0:
                    continue
                product = products.get(to_int(raw_id, "Unknown cookie."))
                if product is None or product["event_price"] is None:
                    raise ValueError("One of those cookies isn't offered for catering.")
                if n < 0 or n % CATERING_STEP != 0:
                    raise ValueError(f"Catering flavors come in sets of {CATERING_STEP}.")
                parts.append(f"{n} {product['name']}")
                tray_count += n
                total += n * product["event_price"]
            if tray_count != size:
                raise ValueError(f"Your {size}-cookie tray has {tray_count} cookies chosen.")
            lines.append(f"Catering tray of {size}: " + ", ".join(parts))
            count += size
            kinds.add("catering")

        else:
            raise ValueError("Something in your basket isn't valid.")

    order_type = kinds.pop() if len(kinds) == 1 else "mixed"
    return "; ".join(lines), count, round(total, 2), order_type


def parse_money(value):
    """Turn text like '$12.99' into 12.99, or raise ValueError."""
    amount = float(str(value or "").replace("$", "").replace(",", "").strip())
    if not math.isfinite(amount) or amount < 0:
        raise ValueError("Not a valid amount.")
    return round(amount, 2)


# ---------------------------------------------------------------------------
# PUBLIC PAGES — anyone can visit these.
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    products = load_products()
    featured = next((p for p in products if p["name"] == FEATURED_FLAVOR), products[0])
    with db() as conn:
        reviews = [dict(r) for r in conn.execute("SELECT author, text FROM reviews ORDER BY id")]
    # The scrolling strip needs enough cards to fill a wide screen, so short lists repeat.
    if reviews:
        reviews = reviews * math.ceil(8 / len(reviews))
    return render_template("index.html", featured=featured, featured_label=FEATURED_LABEL, reviews=reviews)


@app.route("/cookies")
def cookies():
    return render_template("cookies.html", products=load_products("packs"),
                           lowest_pack_price=min(p["price"] for p in PACK_SIZES.values()))


@app.route("/cookies/<int:product_id>")
def cookie_detail(product_id):
    pack_flavors = load_products("packs")
    product = next((p for p in pack_flavors if p["id"] == product_id), None)
    if product is None:
        abort(404)
    others = [p for p in pack_flavors if p["id"] != product_id]
    return render_template("cookie_detail.html", c=product, others=others,
                           packs=PACK_SIZES, max_qty=MAX_PACKS_PER_LINE)


@app.route("/catering")
def catering():
    products = load_products("catering")
    price_each = min(p["event_price"] for p in products)
    return render_template("catering.html", products=products, sizes=CATERING_SIZES,
                           step=CATERING_STEP, price_each=price_each)


@app.route("/basket")
def basket():
    return render_template("basket.html", catering_hint_at=CATERING_HINT_AT)


# ---------------------------------------------------------------------------
# API — data for the page's JavaScript (JSON in, JSON out).
# ---------------------------------------------------------------------------

@app.route("/api/menu")
def get_menu():
    return jsonify({
        "products": load_products(),
        "packs": PACK_SIZES,
        "catering": {"sizes": CATERING_SIZES, "step": CATERING_STEP},
    })


def bad_request(message):
    return jsonify({"error": message}), 400


@app.route("/api/orders", methods=["POST"])
def create_order():
    """Receive the basket at checkout, check it, price it, and save it as one order."""
    data = request.get_json(silent=True) or {}
    customer = str(data.get("customer", "")).strip()[:100]
    email = str(data.get("email", "")).strip()[:200]
    phone = str(data.get("phone", "")).strip()[:40]
    notes = str(data.get("notes", "")).strip()[:1000]

    if not customer or "@" not in email:
        return bad_request("Please enter your name and a valid email.")
    try:
        pickup = date.fromisoformat(str(data.get("pickup_date", "")))
    except ValueError:
        return bad_request("Please choose a pickup date.")
    if pickup < date.today():
        return bad_request("The pickup date can't be in the past.")

    with db() as conn:
        products = {row["id"]: row for row in conn.execute("SELECT * FROM products")}
        try:
            items, count, total, order_type = price_basket(data.get("items"), products)
        except ValueError as error:
            return bad_request(str(error))
        cursor = conn.execute(
            "INSERT INTO orders (customer, contact, order_type, items, cookie_count, total, "
            "order_date, due_date, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (customer, " · ".join(filter(None, [email, phone])), order_type, items,
             count, total, date.today().isoformat(), pickup.isoformat(), notes),
        )
        order_id = cursor.lastrowid

    return jsonify({
        "order_number": f"{order_id:04d}",
        "message": (f"Thanks {customer}! Order #{order_id:04d} ({count} cookies, ${total:.2f}) is in. "
                    f"Pickup in {PICKUP_LOCATION} on {pickup:%A, %B %d}. "
                    f"We'll email you to confirm and arrange payment."),
    }), 201


# ---------------------------------------------------------------------------
# ADMIN — only you, after logging in with your password.
# ---------------------------------------------------------------------------

def login_required(view):
    """Put @login_required above a route to send logged-out visitors to the login page."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapper


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    setup_mode = not PASSWORD_FILE.exists()
    # The very first password can only be created from this computer.
    is_this_computer = request.remote_addr in ("127.0.0.1", "::1")
    error = None

    if request.method == "POST":
        password = request.form.get("password", "")
        if setup_mode:
            if not is_this_computer:
                error = "The admin password can only be created on the owner's computer."
            elif len(password) < 8:
                error = "Use at least 8 characters."
            elif password != request.form.get("confirm", ""):
                error = "The two passwords don't match."
            else:
                # Store a scrambled "hash" of the password, never the password itself.
                PASSWORD_FILE.write_text(generate_password_hash(password))
                session.clear()
                session["is_admin"] = True
                return redirect(url_for("admin_dashboard"))
        elif check_password_hash(PASSWORD_FILE.read_text().strip(), password):
            session.clear()
            session["is_admin"] = True
            return redirect(url_for("admin_dashboard"))
        else:
            error = "Wrong password."

    return render_template("admin_login.html", setup_mode=setup_mode, error=error)


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/admin")
@login_required
def admin_dashboard():
    with db() as conn:
        orders = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
        expenses = conn.execute("SELECT * FROM expenses ORDER BY purchase_date DESC, id DESC").fetchall()
        reviews = conn.execute("SELECT * FROM reviews ORDER BY id DESC").fetchall()

    paid = [o for o in orders if o["status"] == "paid"]
    unpaid = [o for o in orders if o["status"] != "paid"]
    revenue = sum(o["total"] for o in paid)
    spent = sum(e["amount"] for e in expenses)

    return render_template(
        "admin.html",
        orders=orders, expenses=expenses, reviews=reviews,
        revenue=revenue, spent=spent, profit=revenue - spent,
        paid_count=len(paid), unpaid_count=len(unpaid),
        unpaid_total=sum(o["total"] for o in unpaid),
        today=date.today().isoformat(),
    )


@app.route("/admin/orders/<int:order_id>/toggle-paid", methods=["POST"])
@login_required
def admin_toggle_paid(order_id):
    with db() as conn:
        conn.execute(
            "UPDATE orders SET status = CASE status WHEN 'paid' THEN 'unpaid' ELSE 'paid' END WHERE id = ?",
            (order_id,),
        )
    return redirect(url_for("admin_dashboard") + "#orders")


@app.route("/admin/orders/<int:order_id>/delete", methods=["POST"])
@login_required
def admin_delete_order(order_id):
    with db() as conn:
        conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))
    flash(f"Order #{order_id:04d} deleted.", "ok")
    return redirect(url_for("admin_dashboard") + "#orders")


@app.route("/admin/orders/new", methods=["POST"])
@login_required
def admin_add_order():
    """For orders that come in by Instagram DM, text, or in person."""
    form = request.form
    customer, items = form.get("customer", "").strip(), form.get("items", "").strip()
    try:
        total = parse_money(form.get("total"))
        count = int(form.get("cookie_count") or 0)
    except ValueError:
        flash("Total must be a number, like 48 or 48.00.", "error")
        return redirect(url_for("admin_dashboard") + "#orders")
    if not customer or not items:
        flash("Customer and what they ordered are required.", "error")
        return redirect(url_for("admin_dashboard") + "#orders")

    with db() as conn:
        conn.execute(
            "INSERT INTO orders (customer, contact, order_type, items, cookie_count, total, order_date, "
            "due_date, status, payment_info, notes) VALUES (?, ?, 'manual', ?, ?, ?, ?, ?, ?, ?, ?)",
            (customer, form.get("contact", "").strip(), items, count or None, total,
             date.today().isoformat(), form.get("due_date") or None,
             "paid" if form.get("paid") else "unpaid",
             form.get("payment_info", "").strip(), form.get("notes", "").strip()),
        )
    flash(f"Order for {customer} added.", "ok")
    return redirect(url_for("admin_dashboard") + "#orders")


@app.route("/admin/expenses/new", methods=["POST"])
@login_required
def admin_add_expense():
    form = request.form
    item = form.get("item", "").strip()
    try:
        amount = parse_money(form.get("amount"))
        purchase_date = date.fromisoformat(form.get("purchase_date", "")).isoformat()
    except ValueError:
        flash("Enter a date and a cost like 12.99.", "error")
        return redirect(url_for("admin_dashboard") + "#expenses")
    if not item:
        flash("Say what you bought.", "error")
        return redirect(url_for("admin_dashboard") + "#expenses")

    with db() as conn:
        conn.execute(
            "INSERT INTO expenses (purchase_date, item, amount, notes) VALUES (?, ?, ?, ?)",
            (purchase_date, item, amount, form.get("notes", "").strip()),
        )
    flash(f"Added {item} (${amount:.2f}).", "ok")
    return redirect(url_for("admin_dashboard") + "#expenses")


@app.route("/admin/expenses/<int:expense_id>/delete", methods=["POST"])
@login_required
def admin_delete_expense(expense_id):
    with db() as conn:
        conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    flash("Purchase deleted.", "ok")
    return redirect(url_for("admin_dashboard") + "#expenses")


@app.route("/admin/reviews/new", methods=["POST"])
@login_required
def admin_add_review():
    author = request.form.get("author", "").strip()[:80]
    text = request.form.get("text", "").strip()[:500]
    if not author or not text:
        flash("Add both who said it and what they said.", "error")
    else:
        with db() as conn:
            conn.execute("INSERT INTO reviews (author, text) VALUES (?, ?)", (author, text))
        flash(f"Review from {author} added to the home page.", "ok")
    return redirect(url_for("admin_dashboard") + "#reviews")


@app.route("/admin/reviews/<int:review_id>/delete", methods=["POST"])
@login_required
def admin_delete_review(review_id):
    with db() as conn:
        conn.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
    flash("Review removed.", "ok")
    return redirect(url_for("admin_dashboard") + "#reviews")


if __name__ == "__main__":
    init_db()
    app.run(debug=True)  # debug=True auto-reloads when you edit code (dev only!)
