document.documentElement.classList.add("can-reveal");

const revealItems = document.querySelectorAll("[data-reveal]");
const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
      }
    });
  },
  { threshold: 0.14 }
);

revealItems.forEach((item, index) => {
  item.style.setProperty("--delay", `${Math.min(index * 70, 420)}ms`);
  observer.observe(item);
});

setTimeout(() => {
  revealItems.forEach((item) => item.classList.add("is-visible"));
}, 800);

document.querySelectorAll(".resume-card, .generator-card, .auth-card").forEach((card) => {
  card.addEventListener("pointermove", (event) => {
    const rect = card.getBoundingClientRect();
    card.style.setProperty("--x", `${((event.clientX - rect.left) / rect.width) * 100}%`);
    card.style.setProperty("--y", `${((event.clientY - rect.top) / rect.height) * 100}%`);
  });
});
