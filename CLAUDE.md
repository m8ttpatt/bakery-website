# mattpatt_bakes website

The website for Matthew's cookie business, **mattpatt_bakes** (two t's, underscore, lowercase).
Matthew is new to coding and is using this project to learn full-stack development, so
explain changes step by step in plain language and say which files you touched.

## How to run
- `.\.venv\Scripts\python.exe app.py` in this folder → http://127.0.0.1:5000
- Admin dashboard: http://127.0.0.1:5000/admin (password login; first password can only be set from this computer)
- Tests: there is no test file in the repo yet. The earlier ones used Flask's test client
  against a temporary database (override `DB_PATH`, `PASSWORD_FILE`, `COOKIE_PHOTO_DIR` in `app.py`).
- The PC sometimes runs low on memory and the server gets killed; just restart it.
- Shell is Windows PowerShell 5.1: inline `python -c "..."` quoting breaks easily, so write
  small script files instead.

## Stack
Python + Flask, SQLite (`bakery.db`, created automatically), Jinja2 templates
(`templates/base.html` is the shared layout, `_macros.html` has the photo macro),
vanilla JavaScript in `static/*.js`, one stylesheet `static/style.css`.

## Business rules (all enforced server-side in `app.py`; never trust prices from the browser)
- Pickup only, in **New York**, Sat 10am–2pm.
- **Personal packs** (bigger cookies): 6 = $26, 12 = $48, 18 = $70.
  6-packs are 1 flavor; 12 and 18 packs may be **any 1 or 2 flavors** (split evenly: 6+6, 9+9).
  Customers are not forced to include the flavor whose page they're on.
- **Catering** (smaller event cookies, $3.75 each): trays of 24/48/72/96, flavors in steps of 6,
  tray must be filled exactly.
- No hard cap on personal orders; the basket shows a "consider catering" note at 24+ cookies.
- 8 flavors (`MENU` in `app.py`), including Cookies n' Cream on both menus.
- Featured "New fall flavor" on the home page: Cookie Butter Stuffed Biscoff.

## Site structure
- Home: featured flavor (photo left, text + Order button right) → auto-scrolling reviews strip → About.
- Top bar: logo · **Order ▾** dropdown (Cookies / Catering) · About · Basket.
- `/cookies` grid (photos only, no descriptions; hover swaps to a second photo) → `/cookies/<id>` pack picker.
- `/catering` tray builder. `/basket` checkout (called "Basket", never "cart"; stored in localStorage).
- `/admin`: orders (paid/unpaid), money received, ingredient expenses, profit = received − costs, reviews.

## Design
Colors come from the logo (tiger in a green apron): white, orange, green. Tokens are at the top
of `style.css`. Buttons/selected states are green. Fonts: Fraunces (headings) + Inter.
The reviews strip respects "reduce motion" (Matthew's PC has Windows animations off, so it
doesn't scroll there — expected).

## Privacy
- `private/` is gitignored and holds the real order sheet, `past_orders.json`, the secret key
  and the admin password hash. Never move these into `static/` (everything in `static/` is public).
- Never make up reviews or star ratings; real reviews are added through the admin page.

## Photos
Drop files into `static/images/cookies/` named by flavor slug, e.g. `brookie.jpg` and
`brookie-hover.jpg`. Exact names are in `static/images/cookies/PHOTO-NAMES.txt`.

## Open to-dos
- Real cookie photos (placeholders show "Photo coming soon").
- Real customer reviews (add via /admin).
- Confirm 18-pack split (currently 9+9).
- `GUIDE.md` describes the very first version of the site and is out of date.
- Order sheet note: past order #2 lists 78 cookies but the sheet says 75 for $242 — copied as written.
- Not deployed to the internet yet; it only runs on this computer.

## Git
Only commit when Matthew says so.
