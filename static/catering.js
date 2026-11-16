// CATERING PAGE — pick a tray size, then fill it with flavors in sets of 6.

const catering = document.getElementById("catering");
const STEP = Number(catering.dataset.step);
const sizeButtons = catering.querySelectorAll(".size-btn");
const flavorCards = catering.querySelectorAll(".catering-flavor");
const progress = document.getElementById("catering-progress");
const summary = document.getElementById("catering-summary");
const addButton = document.getElementById("add-catering");

let traySize = Number(catering.querySelector(".size-btn.selected").dataset.size);
const counts = {}; // { productId: how many cookies of that flavor }

function chosen() {
  return Object.values(counts).reduce((a, b) => a + b, 0);
}

function update() {
  const total = chosen();
  const left = traySize - total;

  for (const card of flavorCards) {
    const n = counts[card.dataset.id] || 0;
    card.querySelector(".value").textContent = n;
    card.classList.toggle("picked", n > 0);
    card.querySelector('[data-step="-1"]').disabled = n === 0;
    card.querySelector('[data-step="1"]').disabled = left < STEP; // tray is full
  }

  progress.textContent = `(${total} of ${traySize} chosen)`;
  if (left > 0) summary.textContent = `Choose ${left} more cookies.`;
  else if (left < 0) summary.textContent = `That's ${-left} too many for a ${traySize} tray. Remove some, or pick a bigger tray.`;
  else summary.textContent = `Your ${traySize}-cookie tray is full!`;
  addButton.disabled = left !== 0;
}

for (const button of sizeButtons) {
  button.addEventListener("click", () => {
    for (const b of sizeButtons) {
      b.classList.toggle("selected", b === button);
      b.setAttribute("aria-pressed", b === button);
    }
    traySize = Number(button.dataset.size);
    update();
  });
}

for (const card of flavorCards) {
  for (const button of card.querySelectorAll(".stepper button")) {
    button.addEventListener("click", () => {
      const id = card.dataset.id;
      counts[id] = Math.max(0, (counts[id] || 0) + Number(button.dataset.step) * STEP);
      update();
    });
  }
}

addButton.addEventListener("click", () => {
  const flavors = {};
  for (const [id, n] of Object.entries(counts)) if (n > 0) flavors[id] = n;
  Basket.add({ type: "catering", size: traySize, flavors });
  for (const id in counts) delete counts[id];
  showToast(`Added a ${traySize}-cookie catering tray.`, "View basket", "/basket");
  update();
});

update();
