// JAVASCRIPT — runs inside the visitor's browser and makes the page interactive.
// It talks to the backend (app.py) using fetch(), which sends HTTP requests.

const grid = document.getElementById("product-grid");
const select = document.getElementById("product-select");
const form = document.getElementById("order-form");
const message = document.getElementById("form-message");

// 1) Ask the backend for the menu, then build the cards and dropdown from that data.
async function loadMenu() {
  try {
    const response = await fetch("/api/products");    // GET request -> app.py list_products()
    const products = await response.json();           // turn JSON text into JS objects

    grid.innerHTML = "";
    select.innerHTML = "";
    for (const p of products) {
      const card = document.createElement("article");
      card.className = "card";
      card.innerHTML = `
        <div class="emoji">${p.emoji}</div>
        <h3></h3>
        <p></p>
        <div class="price">$${p.price.toFixed(2)}</div>`;
      // textContent (not innerHTML) for text that came from data: safer against injected code.
      card.querySelector("h3").textContent = p.name;
      card.querySelector("p").textContent = p.description;
      grid.appendChild(card);

      select.add(new Option(`${p.name} — $${p.price.toFixed(2)}`, p.id));
    }
  } catch (err) {
    grid.innerHTML = '<p class="muted">Could not load the menu. Is the server running?</p>';
  }
}

// 2) When the form is submitted, send the order to the backend instead of reloading the page.
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(form)); // {customer: "...", email: "...", ...}

  const response = await fetch("/api/orders", {       // POST request -> app.py create_order()
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  const result = await response.json();

  if (response.ok) {
    message.className = "ok";
    message.textContent = result.message;
    form.reset();
  } else {
    message.className = "err";
    message.textContent = result.error;
  }
});

// Don't allow pickup dates in the past.
form.pickup_date.min = new Date().toISOString().split("T")[0];

loadMenu();
