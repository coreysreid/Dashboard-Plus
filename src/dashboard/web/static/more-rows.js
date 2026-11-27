// Load the next page of rows as the person scrolls near the end, or when they press "Show more".
(function () {
  var button = document.getElementById("more");
  var wrap = document.getElementById("more-wrap");
  var body = document.getElementById("rows");
  var busy = false;
  function load() {
    var offset = button.dataset.offset;
    if (busy || !offset) return;
    busy = true;
    var params = new URLSearchParams(window.location.search);
    params.set("offset", offset);
    fetch(button.dataset.rowsUrl + "?" + params.toString(), { credentials: "same-origin" })
      .then(function (r) { return r.text(); })
      .then(function (html) {
        var holder = document.createElement("tbody");
        holder.innerHTML = html;
        var marker = holder.querySelector("[data-next]");
        var next = marker ? marker.dataset.next : "";
        if (marker) marker.remove();
        while (holder.firstChild) body.appendChild(holder.firstChild);
        button.dataset.offset = next;
        if (!next) wrap.hidden = true;
        busy = false;
      })
      .catch(function () { busy = false; });
  }
  button.addEventListener("click", load);
  if ("IntersectionObserver" in window) {
    new IntersectionObserver(function (entries) {
      if (entries[0].isIntersecting) load();
    }, { rootMargin: "400px" }).observe(wrap);
  }
})();
