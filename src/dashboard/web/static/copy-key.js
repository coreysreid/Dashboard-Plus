document.getElementById("copy-key").addEventListener("click", function () {
  var box = document.getElementById("helper-key");
  box.select();
  var say = function (text) { document.getElementById("copied").textContent = text; };
  if (navigator.clipboard) { navigator.clipboard.writeText(box.value).then(function () { say("Copied."); }, function () { say("Select the key and copy it."); }); }
  else { say("Select the key and copy it."); }
});
