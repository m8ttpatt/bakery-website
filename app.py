"""
BACKEND — the "server" half of the website.

When someone visits your site, their browser sends a *request* to this program.
This program decides what to send back: an HTML page, or raw data (JSON).

Run it with:   .venv\Scripts\python.exe app.py
Then open:     http://127.0.0.1:5000
"""

import sqlite3
from pathlib import Path

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
DB_PATH = Path(__file__).parent / "bakery.db"


# ---------------------------------------------------------------------------
# DATABASE — where the site's data lives permanently (survives restarts).
# SQLite stores the whole database in a single file: bakery.db
# ---------------------------------------------------------------------------

def get_db():
    """Open a connection to the database file."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name: row["price"]
    return conn


def init_db():
    """Create the tables (like spreadsheets) and add starter products the first time."""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id          INTEGER PRIMARY KEY,
                name        TEXT NOT NULL,
                description TEXT,
                price       REAL NOT NULL,
                emoji       TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id          INTEGER PRIMARY KEY,
                customer    TEXT NOT NULL,
                email       TEXT NOT NULL,
                product_id  INTEGER NOT NULL REFERENCES products(id),
                quantity    INTEGER NOT NULL,
                pickup_date TEXT NOT NULL,
                notes       TEXT,
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Only add sample products if the table is empty.
        if conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO products (name, description, price, emoji) VALUES (?, ?, ?, ?)",
                [
                    ("Sourdough Loaf", "Naturally leavened, 24-hour fermented, crackly crust.", 9.00, "🍞"),
                    ("Butter Croissant", "Flaky, laminated with European-style butter.", 4.50, "🥐"),
                    ("Cinnamon Roll", "Soft brioche swirl with cream-cheese glaze.", 5.00, "🌀"),
                    ("Chocolate Chip Cookies (6)", "Brown-butter dough, sea-salt finish.", 12.00, "🍪"),
                    ("Seasonal Fruit Pie", "Whole 9-inch pie with whatever is fresh this week.", 28.00, "🥧"),
                    ("Custom Celebration Cake", "6-inch layer cake. Tell us your flavors in the notes!", 45.00, "🎂"),
                ],
            )


# ---------------------------------------------------------------------------
# ROUTES — each one maps a URL to a Python function.
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    """Send the main HTML page to the browser."""
    return render_template("index.html")


@app.route("/api/products")
def list_products():
    """API endpoint: return the menu as JSON data for the frontend's JavaScript."""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM products ORDER BY id").fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/orders", methods=["POST"])
def create_order():
    """API endpoint: receive an order from the form and save it to the database."""
    data = request.get_json(silent=True) or {}

    # VALIDATION: never trust data from the browser — check it on the server.
    required = ["customer", "email", "product_id", "quantity", "pickup_date"]
    missing = [field for field in required if not str(data.get(field, "")).strip()]
    if missing:
        return jsonify({"error": f"Missing: {', '.join(missing)}"}), 400
    try:
        quantity = int(data["quantity"])
        product_id = int(data["product_id"])
    except ValueError:
        return jsonify({"error": "Quantity and product must be numbers."}), 400
    if not 1 <= quantity <= 50:
        return jsonify({"error": "Quantity must be between 1 and 50."}), 400

    with get_db() as conn:
        product = conn.execute("SELECT name, price FROM products WHERE id = ?", (product_id,)).fetchone()
        if product is None:
            return jsonify({"error": "That product doesn't exist."}), 400
        # The "?" placeholders protect against SQL injection attacks.
        conn.execute(
            "INSERT INTO orders (customer, email, product_id, quantity, pickup_date, notes) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (data["customer"].strip(), data["email"].strip(), product_id,
             quantity, data["pickup_date"], data.get("notes", "").strip()),
        )

    total = product["price"] * quantity
    return jsonify({"message": f"Thanks {data['customer'].strip()}! {quantity} × {product['name']} "
                               f"(${total:.2f}) reserved for {data['pickup_date']}."}), 201


@app.route("/admin/orders")
def admin_orders():
    """A simple page for YOU (the owner) to see incoming orders.
    NOTE: before putting the site on the real internet, protect this with a login."""
    with get_db() as conn:
        orders = conn.execute("""
            SELECT o.*, p.name AS product, p.price * o.quantity AS total
            FROM orders o JOIN products p ON p.id = o.product_id
            ORDER BY o.created_at DESC
        """).fetchall()
    return render_template("orders.html", orders=orders)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)  # debug=True auto-reloads when you edit code (dev only!)
