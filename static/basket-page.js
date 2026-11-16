// BASKET PAGE — list what's in the basket, let people change it, and send the order.

const list = document.getElementById("basket-items");
const form = document.getElementById("checkout-form");
const message = document.getElementById("form-message");
let MENU = null; // names, prices and photos, loaded from the server

function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text; // textContent is safe against injected code
  if (className) node.className = className;
  return node;
}

const productById = (id) => MENU.products.find((p) => p.id === Number(id));

// What one basket line costs. (Display only: the server recalculates the real price.)
function linePrice(item) {
  if (item.type === "pack") return MENU.packs[item.size].price * item.qty;
  return Object.entries(item.flavors).reduce((sum, [id, n]) => sum + n * productById(id).event_price, 0);
}

function thumbnail(product) {
  const box = el("div", undefined, "photo");
  if (product && product.image) {
    const img = el("img");
    img.src = product.image;
    img.alt = "";
    box.append(img);
  } else {
    box.append(el("div", undefined, "placeholder"));
  }
  return box;
}

function render() {
  // Drop anything that no longer exists on the menu.
  let items = Basket.read().filter((item) =>
    item.type === "pack"
      ? packFlavors(item).length > 0 && packFlavors(item).every(productById) && MENU.packs[item.size]
      : item.flavors && Object.keys(item.flavors).every(productById));
  Basket.write(items);

  document.getElementById("basket-empty").hidden = items.length > 0;
  document.getElementById("basket-full").hidden = items.length === 0;
  list.innerHTML = "";

  items.forEach((item, index) => {
    const li = el("li", undefined, "basket-item");
    const info = el("div");

    if (item.type === "pack") {
      const flavors = packFlavors(item).map(productById);
      const each = item.size / flavors.length;
      li.append(thumbnail(flavors[0]));
      info.append(el("h3", flavors.map((f) => f.name).join(" + ")),
                  el("p", `${item.size}-cookie pack${flavors.length > 1 ? ` (${each} + ${each})` : ""} · ~4"`, "muted small"));

      const stepper = el("div", undefined, "stepper small-stepper");
      const minus = el("button", "−");
      const value = el("span", item.qty, "value");
      const plus = el("button", "+");
      minus.type = plus.type = "button";
      minus.setAttribute("aria-label", "One less");
      plus.setAttribute("aria-label", "One more");
      minus.disabled = item.qty <= 1;
      plus.disabled = item.qty >= 10;
      minus.onclick = () => { item.qty -= 1; Basket.write(items); render(); };
      plus.onclick = () => { item.qty += 1; Basket.write(items); render(); };
      stepper.append(minus, value, plus);
      info.append(stepper);
    } else {
      li.append(thumbnail(null));
      const flavors = Object.entries(item.flavors).map(([id, n]) => `${n} ${productById(id).name}`).join(", ");
      info.append(el("h3", `Catering tray · ${item.size} cookies`), el("p", flavors, "muted small"));
    }

    const remove = el("button", "Remove", "link-btn danger");
    remove.type = "button";
    remove.onclick = () => { items.splice(index, 1); Basket.write(items); render(); };
    info.append(remove);

    li.append(info, el("strong", money(linePrice(item)), "price"));
    list.append(li);
  });

  const total = items.reduce((sum, item) => sum + linePrice(item), 0);
  document.getElementById("basket-total").textContent = money(total);

  // Big pack orders get a friendly catering suggestion (it never blocks the order).
  const hint = document.getElementById("catering-hint");
  const packCookies = items.filter((i) => i.type === "pack").reduce((sum, i) => sum + i.size * i.qty, 0);
  hint.hidden = packCookies < Number(hint.dataset.at);
}

// Send the whole basket to the server as one order.
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = form.querySelector("button[type=submit]");
  button.disabled = true;
  message.className = "";
  message.textContent = "Sending…";

  try {
    const response = await fetch("/api/orders", {   // POST request -> app.py create_order()
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...Object.fromEntries(new FormData(form)), items: Basket.read() }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error);

    Basket.clear();
    document.getElementById("basket-full").hidden = true;
    document.getElementById("done-message").textContent = result.message;
    document.getElementById("order-done").hidden = false;
  } catch (err) {
    message.className = "err";
    message.textContent = err.message || "Something went wrong. Please try again.";
  } finally {
    button.disabled = false;
  }
});

// Don't allow pickup dates in the past (uses the visitor's local date).
const now = new Date();
form.pickup_date.min = new Date(now - now.getTimezoneOffset() * 60000).toISOString().split("T")[0];

(async function start() {
  try {
    MENU = await (await fetch("/api/menu")).json();
    render();
  } catch {
    list.textContent = "Could not load your basket. Is the server running?";
    document.getElementById("basket-full").hidden = false;
  }
})();
