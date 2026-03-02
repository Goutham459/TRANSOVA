// THEME & FILTER INTERACTIONS
document.addEventListener("DOMContentLoaded", () => {

    /* ===============================
       FILTER PANEL TOGGLE (MOBILE)
    =============================== */
    const filterToggle = document.getElementById("filter-toggle");
    const filterPanel = document.getElementById("filter-panel");

    if (filterToggle && filterPanel) {
        filterToggle.addEventListener("click", () => {
            filterPanel.classList.toggle("show");
        });
    }

    /* ===============================
       TRUCK CARD ENTRANCE ANIMATION
    =============================== */
    document.querySelectorAll(".truck-card").forEach((card, index) => {
        card.style.animation = `fadeUp 0.6s ease forwards`;
        card.style.animationDelay = `${index * 0.08}s`;
    });

});

/* ===============================
   KEYFRAMES (Injected Once)
=============================== */
const style = document.createElement("style");
style.innerHTML = `
@keyframes fadeUp {
    from {
        opacity: 0;
        transform: translateY(24px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}
`;
document.head.appendChild(style);