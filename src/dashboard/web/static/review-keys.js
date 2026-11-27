// Review keys (decision 0101). Only a convenience: every button works without this script.
(function () {
  var rows = Array.prototype.slice.call(document.querySelectorAll("[data-row]"));
  if (!rows.length) return;
  document.getElementById("review-keys").hidden = false;
  var current = -1, count = document.getElementById("ticked-count");
  function remember(index) { try { sessionStorage.setItem("review-row", String(index)); } catch (e) {} }
  function show(index, focus) {
    if (current >= 0 && rows[current]) rows[current].classList.remove("current");
    current = Math.max(0, Math.min(rows.length - 1, index));
    var row = rows[current];
    row.classList.add("current");
    if (focus) { row.focus({ preventScroll: true }); row.scrollIntoView({ block: "nearest" }); }
  }
  function ticked() {
    var n = document.querySelectorAll("[data-row] input[type=checkbox]:checked").length;
    count.textContent = n ? n + " ticked:" : "Tick rows, then:";
  }
  function groupOf(box) {
    var group = box.closest("[data-group]");
    return group ? group.querySelectorAll("input[type=checkbox]") : [box];
  }
  document.addEventListener("change", function (event) {
    var box = event.target;
    if (!box.matches || !box.matches("[data-row] input[type=checkbox]")) return;
    Array.prototype.forEach.call(groupOf(box), function (other) { other.checked = box.checked; });
    ticked();
  });
  rows.forEach(function (row, index) {
    row.addEventListener("click", function () { show(index, false); });
  });
  document.addEventListener("submit", function () { if (current >= 0) remember(current); });
  var start = 0;
  try { start = parseInt(sessionStorage.getItem("review-row") || "0", 10) || 0; sessionStorage.removeItem("review-row"); } catch (e) {}
  show(start, false);
  ticked();
  document.addEventListener("keydown", function (event) {
    if (event.ctrlKey || event.metaKey || event.altKey) return;
    var target = event.target;
    if (target.closest && target.closest("input, textarea, select, [contenteditable]")) return;
    var key = event.key, row = rows[current];
    if (key === "ArrowDown" || key === "j" || key === "J") { event.preventDefault(); show(current + 1, true); return; }
    if (key === "ArrowUp" || key === "k" || key === "K") { event.preventDefault(); show(current - 1, true); return; }
    if (!row) return;
    if (key === " " && !(target.closest && target.closest("button, a, summary"))) {
      event.preventDefault();
      var box = row.querySelector("input[type=checkbox]");
      box.checked = !box.checked;
      box.dispatchEvent(new Event("change", { bubbles: true }));
      return;
    }
    var button = key === "a" || key === "A" ? row.querySelector("[data-accept]")
               : key === "r" || key === "R" ? row.querySelector("[data-reject]") : null;
    if (button) { event.preventDefault(); remember(current); button.click(); }
  });
})();
