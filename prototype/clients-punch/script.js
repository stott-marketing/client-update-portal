const filterButtons = document.querySelectorAll(".filter-button");
const cards = document.querySelectorAll(".update-card");

filterButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const filter = button.dataset.filter;

    filterButtons.forEach((item) => item.classList.remove("active"));
    button.classList.add("active");

    cards.forEach((card) => {
      const isVisible = filter === "all" || card.dataset.status === filter;
      card.classList.toggle("hidden", !isVisible);
    });
  });
});

document.querySelectorAll(".archive-item").forEach((item) => {
  item.addEventListener("click", () => {
    document.querySelectorAll(".archive-item").forEach((entry) => entry.classList.remove("current"));
    item.classList.add("current");
  });
});
