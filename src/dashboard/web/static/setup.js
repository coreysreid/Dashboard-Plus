(function () {
  var button = document.getElementById("add-pet");
  if (!button) return;
  button.addEventListener("click", function () {
    var next = document.querySelector(".pet-slot[hidden]");
    if (next) { next.hidden = false; next.querySelector("input").focus(); }
    if (!document.querySelector(".pet-slot[hidden]")) button.hidden = true;
  });
})();
(function () {
  var button = document.getElementById("add-person");
  if (!button) return;
  button.addEventListener("click", function () {
    var next = document.querySelector(".person-slot[hidden]");
    if (next) { next.hidden = false; next.querySelector("input").focus(); }
    if (!document.querySelector(".person-slot[hidden]")) button.hidden = true;
  });
})();
var zone = "";
try { zone = Intl.DateTimeFormat().resolvedOptions().timeZone || ""; document.getElementById("timezone").value = zone; } catch (e) {}
(function () {
  // Country and state: the state list follows the country, and a first guess comes from the time zone.
  var country = document.getElementById("country"), region = document.getElementById("region");
  if (!country || !region) return;
  var regions = JSON.parse(country.dataset.regions), guesses = JSON.parse(country.dataset.guesses);
  function show(id, on) { document.getElementById(id).hidden = !on; }
  function fill(chosen) {
    var keep = region.value;
    region.innerHTML = '<option value="">(choose)</option>';
    (regions[country.value] || []).forEach(function (name) {
      var option = document.createElement("option");
      option.value = option.textContent = name;
      if (name === (chosen || keep)) option.selected = true;
      region.appendChild(option);
    });
    var other = country.value === "other";
    show("country-other", other); show("region-other", other); show("region-list", !other);
  }
  country.addEventListener("change", function () { show("place-guess", false); fill(""); });
  if (country.dataset.guess === "yes" && !country.value && guesses[zone]) {
    country.value = guesses[zone][0];
    fill(guesses[zone][1]);
    show("place-guess", true);
  }
})();
