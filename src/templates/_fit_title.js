// Başlığı kutusuna sığdırır: 54px'ten 42px'e kademeli küçültür,
// en küçük boyutta da sığmazsa satır sayısını kırpıp "…" ekler.
// Bitince document.title = "fitted" yapar — Playwright bunu bekler.
function fitTitle() {
  const t = document.getElementById("title");
  const box = document.getElementById("titlebox");
  let size = 54;
  t.style.fontSize = size + "px";
  while (size > 42 && t.scrollHeight > box.clientHeight) {
    size -= 2;
    t.style.fontSize = size + "px";
  }
  if (t.scrollHeight > box.clientHeight) {
    const lineHeight = size * 1.26;
    const lines = Math.max(1, Math.floor(box.clientHeight / lineHeight));
    t.style.display = "-webkit-box";
    t.style.webkitBoxOrient = "vertical";
    t.style.webkitLineClamp = lines;
    t.style.overflow = "hidden";
  }
  document.title = "fitted";
}
document.fonts.ready.then(fitTitle);
