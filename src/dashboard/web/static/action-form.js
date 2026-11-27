// Typing a date for the next reminder chooses "Choose a date".
(function () {
  var typed = document.getElementById("f-next_date"), choice = document.getElementById("next-date-choice");
  if (typed && choice) typed.addEventListener("input", function () { if (typed.value.trim()) choice.checked = true; });
})();
// The repeat's offer follows Done on, worked out the same way as dashboard/core/dates.py add_period.
// The server works it out again when saving, so this is only what the page shows.
(function () {
  var box = document.getElementById("next-choices"), words = document.getElementById("repeat-words");
  if (!box || !words || !box.dataset.repeatCount) return;
  var from = document.getElementById(box.dataset.dateFrom), style = box.dataset.style;
  var count = +box.dataset.repeatCount, unit = box.dataset.repeatUnit;
  function read(text) {
    var m = /^(\d{4})-(\d{1,2})-(\d{1,2})$/.exec(text), y, mo, d;
    if (m) { y = +m[1]; mo = +m[2]; d = +m[3]; }
    else {
      m = /^(\d{1,2})\s*[\/.\-]\s*(\d{1,2})\s*[\/.\-]\s*(\d{2}|\d{4})$/.exec(text);
      if (!m || style === "ymd") return null;
      d = style === "mdy" ? +m[2] : +m[1]; mo = style === "mdy" ? +m[1] : +m[2];
      y = +m[3] + (m[3].length === 2 ? 2000 : 0);
    }
    var when = new Date(Date.UTC(y, mo - 1, d));
    return when.getUTCFullYear() === y && when.getUTCMonth() === mo - 1 && when.getUTCDate() === d ? [y, mo, d] : null;
  }
  function add(y, mo, d) {
    if (unit === "weeks" || unit === "days") { var w = new Date(Date.UTC(y, mo - 1, d + (unit === "weeks" ? 7 : 1) * count)); return [w.getUTCFullYear(), w.getUTCMonth() + 1, w.getUTCDate()]; }
    var index = y * 12 + (mo - 1) + count * (unit === "years" ? 12 : 1), ny = Math.floor(index / 12), nm = index % 12;
    var last = new Date(Date.UTC(ny, nm + 1, 0)).getUTCDate();
    return [ny, nm + 1, Math.min(d, last)];
  }
  function show(p) {
    var two = function (n) { return (n < 10 ? "0" : "") + n; }, yy = p[0] >= 2000 && p[0] <= 2099 ? two(p[0] % 100) : "" + p[0];
    if (style === "ymd") return p[0] + "-" + two(p[1]) + "-" + two(p[2]);
    return style === "mdy" ? two(p[1]) + "/" + two(p[2]) + "/" + yy : two(p[2]) + "/" + two(p[1]) + "/" + yy;
  }
  function update() {
    var day = from && read(from.value.trim());
    words.textContent = day ? "Use " + show(add(day[0], day[1], day[2])) + " from your repeat" : "Use the date from your repeat";
  }
  if (from) from.addEventListener("input", update);
})();
