document.addEventListener("DOMContentLoaded", function () {
  // Dismiss flash messages
  document.querySelectorAll(".flash-close").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var flash = btn.closest(".flash");
      if (flash) flash.remove();
    });
  });

  // Expand/collapse envelope cards
  document.querySelectorAll(".envelope-summary").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var card = btn.closest(".envelope-card");
      var isOpen = card.classList.toggle("is-open");
      btn.setAttribute("aria-expanded", isOpen ? "true" : "false");
    });
  });

  // Loading state on the connect form (IMAP calls can take a few seconds)
  var form = document.getElementById("connect-form");
  if (form) {
    form.addEventListener("submit", function () {
      var submitBtn = document.getElementById("connect-submit");
      if (submitBtn) {
        submitBtn.classList.add("is-loading");
        submitBtn.disabled = true;
      }
    });
  }
});
