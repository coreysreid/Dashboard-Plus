// One listener for every Copy button on the page, including the starting messages further down.
document.addEventListener("click", function (event) {
  var button = event.target.closest ? event.target.closest(".copy-block") : null;
  if (!button) { return; }
  var text = document.getElementById(button.dataset.copy).textContent;
  var say = function (words) { document.getElementById(button.dataset.say).textContent = words; };
  if (navigator.clipboard) { navigator.clipboard.writeText(text).then(function () { say("Copied."); }, function () { say("Select the text and copy it."); }); }
  else { say("Select the text and copy it."); }
});
