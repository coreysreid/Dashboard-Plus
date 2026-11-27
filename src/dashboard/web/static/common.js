// Private details are never in the page; "Show" asks for just the one wanted, by a POST with this page's session
// token (decisions 0059 and 0123). Without this script the same button submits the form and opens a small page.
document.addEventListener("click", function (event) {
  var button = event.target.closest("[data-reveal], [data-reveal-field]");
  if (!button || !window.fetch || !window.FormData) return;
  event.preventDefault();
  var data = new FormData(document.getElementById("reveal-form"));
  data.set("column", button.value);
  fetch(button.getAttribute("formaction"), {method: "POST", body: data, credentials: "same-origin",
    headers: {"Accept": "application/json"}}).then(function (r) { return r.ok ? r.json() : null; }).then(function (found) {
    if (!found) return;
    if (button.hasAttribute("data-reveal")) {
      var span = document.createElement("span"); span.textContent = found.text; span.tabIndex = -1;
      button.replaceWith(span); span.focus();
      return;
    }
    var id = button.dataset.field, field = document.getElementById(id);
    if (field.type === "checkbox") field.checked = String(found.value) === "1"; else field.value = found.value;
    field.hidden = false;
    var box = document.getElementById(id + "-box"); if (box) box.hidden = false;
    var keep = document.getElementById(id + "-keep"); if (keep) keep.remove();
    document.getElementById(id + "-closed").remove();
    field.focus();
  });
});
// A folded panel (decision 0131) is opened while printing so the paper has every part, then folded again.
var folded = [];
window.addEventListener("beforeprint", function () {
  folded = Array.prototype.filter.call(document.querySelectorAll("details[data-print-open]"), function (d) { return !d.open; });
  folded.forEach(function (d) { d.open = true; });
});
window.addEventListener("afterprint", function () { folded.forEach(function (d) { d.open = false; }); folded = []; });

// One press shows every private cell of that list, each still fetched on its own (decision 0059).
document.addEventListener("click", function (event) {
  var all = event.target.closest("[data-reveal-all]");
  if (!all) return;
  document.getElementById(all.dataset.revealAll).querySelectorAll("[data-reveal]").forEach(function (b) { b.click(); });
  all.remove();
});
// Print buttons (data-print), confirmation questions on forms (data-confirm) and send-once forms (data-once).
document.addEventListener("click", function (event) {
  if (event.target.closest && event.target.closest("[data-print]")) window.print();
});
document.addEventListener("submit", function (event) {
  var form = event.target;
  if (form.dataset && form.dataset.confirm && !window.confirm(form.dataset.confirm)) { event.preventDefault(); return; }
  // Send once: a second click while the first is on its way does nothing (the server also refuses a repeat).
  if (form.dataset && "once" in form.dataset) {
    if (form.dataset.sent) { event.preventDefault(); return; }
    form.dataset.sent = "1";
  }
});
