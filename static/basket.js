// SHARED JAVASCRIPT — loaded on every shop page (see base.html).
// The basket lives in the visitor's browser storage ("localStorage"), so it is remembered
// as they move between pages. Nothing is sent to the server until they place the order.

const BASKET_KEY = "mattpatt_basket";

const Basket = {
  read() {
    try {
      const items = JSON.parse(localStorage.getItem(BASKET_KEY));
      return Array.isArray(items) ? items : [];
    } catch {
      return []; // storage blocked or broken: start with an empty basket
    }
  },

  write(items) {
    try {
      localStorage.setItem(BASKET_KEY, JSON.stringify(items));
    } catch {
      /* storage blocked (e.g. private browsing): the basket just won't be remembered */
    }
    updateBasketCount();
  },

  add(item) {
    const items = this.read();
    // Adding the exact same pack again (same size + same flavors) just increases the quantity.
    const key = (i) => `${i.size}:${packFlavors(i).slice().sort().join(",")}`;
    const same = item.type === "pack" && items.find((i) => i.type === "pack" && key(i) === key(item));
    if (same) same.qty += item.qty;
    else items.push(item);
    this.write(items);
  },

  clear() {
    this.write([]);
  },
};

// The flavor ids in a pack. (Older baskets stored them as product_id + second_id.)
function packFlavors(item) {
  return item.flavors || [item.product_id, item.second_id].filter(Boolean);
}

// How many things are in the basket (a pack counted once per quantity, a tray counted once).
function basketCount() {
  return Basket.read().reduce((sum, item) => sum + (item.type === "pack" ? item.qty : 1), 0);
}

function updateBasketCount() {
  const badge = document.getElementById("basket-count");
  if (!badge) return;
  const n = basketCount();
  badge.textContent = n;
  badge.hidden = n === 0;
}

const money = (n) => `$${Number(n).toFixed(2)}`;

// Show a small message at the bottom of the screen, with an optional link.
let toastTimer;
function showToast(text, linkText, linkHref) {
  const toast = document.getElementById("toast");
  toast.textContent = text;
  if (linkText) {
    const link = document.createElement("a");
    link.href = linkHref;
    link.textContent = linkText;
    toast.append(link);
  }
  toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (toast.hidden = true), 3500);
}

updateBasketCount();
