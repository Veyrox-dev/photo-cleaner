// Shared website bundle: lightweight behavior used by all pages.
(function () {
    var yearNodes = document.querySelectorAll('[data-current-year]');
    if (yearNodes.length > 0) {
        var currentYear = String(new Date().getFullYear());
        yearNodes.forEach(function (node) {
            node.textContent = currentYear;
        });
    }

    var mobileMenuBtn = document.querySelector('.mobile-menu-btn');
    var navLinks = document.getElementById('navLinks');
    if (mobileMenuBtn && navLinks) {
        mobileMenuBtn.addEventListener('click', function () {
            mobileMenuBtn.classList.toggle('active');
            navLinks.classList.toggle('active');
        });
    }
})();
