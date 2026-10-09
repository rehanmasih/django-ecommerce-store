/* Small progressive enhancements. Every feature also works without JavaScript (except the mobile menu toggle). */
(function () {
  "use strict";

  // Mobile navigation
  var toggle = document.querySelector("[data-nav-toggle]");
  var nav = document.querySelector("[data-nav]");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  // Close dropdown menus when clicking elsewhere
  document.addEventListener("click", function (e) {
    document.querySelectorAll("details.dropdown[open]").forEach(function (d) {
      if (!d.contains(e.target)) d.removeAttribute("open");
    });
  });

  // Dismissible messages
  document.querySelectorAll("[data-dismiss]").forEach(function (btn) {
    btn.addEventListener("click", function () { btn.closest(".message").remove(); });
  });

  // Quantity steppers (product page and cart page)
  document.querySelectorAll("[data-qty]").forEach(function (box) {
    var input = box.querySelector("input");
    var max = parseInt(input.getAttribute("max"), 10) || 999;
    box.querySelectorAll("[data-step]").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        if (box.hasAttribute("data-submit")) return; // cart buttons submit their own form
        e.preventDefault();
        var next = (parseInt(input.value, 10) || 1) + parseInt(btn.getAttribute("data-step"), 10);
        input.value = Math.min(Math.max(next, 1), max);
      });
    });
  });

  // Shop filters: apply category / sort immediately
  document.querySelectorAll("[data-autosubmit]").forEach(function (el) {
    el.addEventListener("change", function () { el.form.submit(); });
  });
})();
