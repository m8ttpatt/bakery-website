# How This Website Was Built — A Beginner's Step-by-Step Guide

## The big picture: what "full stack" means

```
  ┌──────────────────────┐    HTTP request     ┌──────────────────────┐        ┌─────────────┐
  │  FRONTEND (browser)  │ ──────────────────▶ │   BACKEND (server)   │ ─────▶ │  DATABASE   │
  │  HTML  = structure   │                     │   app.py (Python +   │  SQL   │  bakery.db  │
  │  CSS   = style       │ ◀────────────────── │   Flask)             │ ◀───── │  (SQLite)   │
  │  JS    = behavior    │   HTML or JSON      │                      │        │             │
  └──────────────────────┘                     └──────────────────────┘        └─────────────┘
```

- **Frontend**: everything that runs in the visitor's browser.
- **Backend**: a program on a server that receives requests, applies rules, and talks to the database.
- **Database**: permanent storage, made of tables like spreadsheets (`products`, `orders`).
- **"Full stack"** = being able to build all three layers.

## Project layout

```
bakery-website/
├── app.py               ← backend: routes, validation, database code
├── bakery.db            ← database file (created automatically on first run)
├── templates/
│   ├── index.html       ← the main page's structure
│   └── orders.html      ← owner's order list (/admin/orders)
├── static/
│   ├── style.css        ← colors, fonts, layout
│   └── script.js        ← browser code: loads menu, submits orders
├── .venv/               ← this project's private copy of Python + Flask
└── GUIDE.md             ← you are here
```

## The steps, in order

### Step 1: Set up the tools
```powershell
mkdir bakery-website; cd bakery-website
python -m venv .venv                         # create an isolated Python environment
.\.venv\Scripts\python.exe -m pip install flask   # install the Flask web framework
```
*Why a virtual environment?* Each project gets its own library versions, so projects can't break each other.
You'll do the same thing for quant projects (with `numpy`, `pandas`, `scipy`…).

### Step 2: Design the data (database)
Before writing code, decide **what you need to store**. Here there are two tables:
- `products`: id, name, description, price, emoji
- `orders`: id, customer, email, product_id → points to a product, quantity, pickup_date, notes

See `init_db()` in `app.py`. `CREATE TABLE` is SQL, the language databases speak.

### Step 3: Build the backend (API)
In `app.py`, each `@app.route(...)` connects a URL to a Python function:

| URL                  | Method | What it does                                  |
|----------------------|--------|-----------------------------------------------|
| `/`                  | GET    | Sends the home page HTML                      |
| `/api/products`      | GET    | Returns the menu as JSON data                 |
| `/api/orders`        | POST   | Validates and saves a new order               |
| `/admin/orders`      | GET    | Shows all orders to you, the owner            |

**GET** = "give me something". **POST** = "here's new data, save it".
**JSON** looks like `{"name": "Croissant", "price": 4.5}`. It's how frontend and backend exchange data.

### Step 4: Build the page structure (HTML)
`templates/index.html` lays out sections: nav, hero, menu, order form, about.
The menu grid starts **empty** on purpose, because JavaScript fills it with data from the database.

### Step 5: Style it (CSS)
`static/style.css`. Try this first: change `--crust: #b5651d;` at the top to `#7b4bb7`, save, and refresh.
The whole site re-colors. Variables like these keep a design consistent.

### Step 6: Make it interactive (JavaScript)
`static/script.js` does two things:
1. `fetch("/api/products")` asks the backend for the menu, then builds the cards.
2. When the form is submitted, it `POST`s the order to `/api/orders` and shows the reply.

### Step 7: Run and test it
```powershell
.\.venv\Scripts\python.exe app.py
```
Open http://127.0.0.1:5000. Place an order, then visit http://127.0.0.1:5000/admin/orders.
Stop the server with `Ctrl+C`.

### Step 8: Save your progress with Git
```powershell
git add .
git commit -m "Describe what you changed"
```
Git takes snapshots so you can always go back. Later you can push to GitHub to back up and share your code.

## Follow a single order through the whole stack
1. You click **Send order** → `script.js` collects the form fields.
2. JS sends `POST /api/orders` with JSON to the server.
3. `create_order()` in `app.py` checks the data (missing fields? valid quantity?).
4. It runs an SQL `INSERT` → a new row lands in `bakery.db`.
5. The server replies `201 Created` + a message → JS shows it in green.
6. `/admin/orders` runs an SQL `SELECT … JOIN` to list orders with product names and totals.

## Exercises to learn by doing
1. **Easy**: Change the bakery name, the about text, and the pickup hours in `index.html`.
2. **Easy**: Add a new product to the list in `init_db()`. *(Delete `bakery.db` first so it re-seeds.)*
3. **Medium**: Add a `phone` field to the order form. You'll need to touch HTML, JS, the SQL table, and validation.
4. **Medium**: Add a "category" (Bread / Pastry / Cake) to products and group the menu by it.
5. **Harder**: Password-protect `/admin/orders`.
6. **Harder**: Deploy it to the internet (e.g. Render, Railway, or PythonAnywhere).

## Before going live (real customers)
- [ ] Protect `/admin/orders` with a login
- [ ] Turn off `debug=True`
- [ ] Send yourself an email when an order arrives
- [ ] Use a hosting service + your own domain name
- [ ] Add real photos of your baking (put them in `static/` and use `<img>` tags)
