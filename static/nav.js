// TOP BAR — the "Order" dropdown.
// With a mouse, CSS opens it on hover. This script adds click/tap and keyboard support,
// because phones can't hover.

const orderMenu = document.getElementById("order-menu");
const orderToggle = orderMenu.querySelector(".dropdown-toggle");

function setMenuOpen(open) {
  orderMenu.classList.toggle("open", open);
  orderToggle.setAttribute("aria-expanded", open);
}

orderToggle.addEventListener("click", (event) => {
  // A mouse already opens the menu by hovering, so a mouse click shouldn't "lock" it open.
  // Taps and the keyboard (Enter/Space) still toggle it.
  if (event.pointerType === "mouse" && window.matchMedia("(hover: hover)").matches) return;
  setMenuOpen(!orderMenu.classList.contains("open"));
});

// Close it when clicking anywhere else, pressing Escape, or tabbing away.
document.addEventListener("click", (event) => {
  if (!orderMenu.contains(event.target)) setMenuOpen(false);
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && orderMenu.classList.contains("open")) {
    setMenuOpen(false);
    orderToggle.focus();
  }
});
orderMenu.addEventListener("focusout", (event) => {
  // relatedTarget is where focus went. It's empty when you tap a blank spot inside the menu,
  // so only close when focus clearly moved somewhere else (outside clicks are handled above).
  if (event.relatedTarget && !orderMenu.contains(event.relatedTarget)) setMenuOpen(false);
});
