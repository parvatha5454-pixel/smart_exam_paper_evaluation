document.addEventListener("DOMContentLoaded", function () {
    // Mobile sidebar toggle
    const sidebarToggle = document.getElementById("sidebarToggle");
    const sidebar = document.getElementById("sidebar");
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener("click", function () {
            sidebar.classList.toggle("show");
        });
    }

    // Dark / light mode toggle (preference saved for the session via localStorage)
    const themeToggle = document.getElementById("themeToggle");
    const htmlEl = document.documentElement;

    const savedTheme = localStorage.getItem("theme");
    if (savedTheme) {
        htmlEl.setAttribute("data-bs-theme", savedTheme);
    }

    if (themeToggle) {
        themeToggle.addEventListener("click", function () {
            const current = htmlEl.getAttribute("data-bs-theme");
            const next = current === "dark" ? "light" : "dark";
            htmlEl.setAttribute("data-bs-theme", next);
            localStorage.setItem("theme", next);
        });
    }
});
