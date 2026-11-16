// PRODUCT PAGE — pick a pack size, 1 or 2 flavors, and a quantity, then add to the basket.

const product = document.getElementById("product");
const sizeButtons = document.querySelectorAll("#pack-sizes .size-btn");
const chips = [...document.querySelectorAll("#flavor-chips .chip")];
const flavorNote = document.getElementById("flavor-note");
const qtyLabel = document.getElementById("qty");
const addButton = document.getElementById("add-to-basket");
const maxQty = Number(product.dataset.maxQty);

let selectedSize = document.querySelector("#pack-sizes .size-btn.selected");
let picked = [Number(product.dataset.productId)]; // flavor ids, in the order they were clicked
let qty = 1;

const maxFlavors = () => Number(selectedSize.dataset.maxFlavors);
const nameOf = (id) => chips.find((c) => Number(c.dataset.id) === id).textContent;

function update() {
  const size = Number(selectedSize.dataset.size);
  picked = picked.slice(-maxFlavors()); // e.g. switching 12 -> 6 keeps only the latest flavor

  for (const b of sizeButtons) {
    b.classList.toggle("selected", b === selectedSize);
    b.setAttribute("aria-pressed", b === selectedSize);
  }
  for (const chip of chips) {
    const on = picked.includes(Number(chip.dataset.id));
    chip.classList.toggle("selected", on);
    chip.setAttribute("aria-pressed", on);
  }

  // Explain the split, e.g. "6 S'mores + 6 Brookie".
  if (maxFlavors() === 1) flavorNote.textContent = "(pick 1)";
  else if (picked.length === 1) flavorNote.textContent = `(pick up to 2: all ${size} ${nameOf(picked[0])})`;
  else flavorNote.textContent = `(${picked.map((id) => `${size / 2} ${nameOf(id)}`).join(" + ")})`;

  qtyLabel.textContent = qty;
  addButton.textContent = `Add to basket · ${money(Number(selectedSize.dataset.price) * qty)}`;
  document.querySelector('#qty-stepper [data-step="-1"]').disabled = qty <= 1;
  document.querySelector('#qty-stepper [data-step="1"]').disabled = qty >= maxQty;
}

for (const button of sizeButtons) {
  button.addEventListener("click", () => {
    selectedSize = button;
    update();
  });
}

for (const chip of chips) {
  chip.addEventListener("click", () => {
    const id = Number(chip.dataset.id);
    if (picked.includes(id)) {
      // Clicking a picked flavor un-picks it, but at least one flavor must stay.
      if (picked.length > 1) picked = picked.filter((p) => p !== id);
    } else {
      // Add it. If that's too many, the oldest pick is dropped.
      picked = [...picked, id].slice(-maxFlavors());
    }
    update();
  });
}

for (const button of document.querySelectorAll("#qty-stepper button")) {
  button.addEventListener("click", () => {
    qty = Math.min(maxQty, Math.max(1, qty + Number(button.dataset.step)));
    update();
  });
}

addButton.addEventListener("click", () => {
  const size = Number(selectedSize.dataset.size);
  Basket.add({ type: "pack", flavors: [...picked], size, qty });
  showToast(`Added ${qty} × ${size}-pack to your basket.`, "View basket", "/basket");
  qty = 1;
  update();
});

update();
