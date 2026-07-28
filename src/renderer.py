"""
HTML/CSS şablonlarını Playwright (headless Chromium) ile PNG'ye çevirir.
Tasarım templates/ altındaki Jinja2 şablonlarında yaşar; piksel hesabı,
satır sarma ve font sığdırma işini CSS + şablon içi script yapar.
"""

import atexit
import base64
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

CANVAS_W, CANVAS_H = 1080, 1350  # 4:5 — kare kullanılmaz

TEMPLATES = {
    "A": "a_side_image.html",       # beyaz asimetrik — kavramsal konular
    "B": "b_split_vertical.html",   # üst fotoğraf + lacivert panel — ürün/nesne odaklı
    "C": "c_image_background.html", # tam ekran fotoğraf + overlay — dramatik haberler
}
DEFAULT_TEMPLATE = "A"

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_FONTS_URI = (Path(__file__).parent / "fonts").resolve().as_uri()

_env = Environment(loader=FileSystemLoader(_TEMPLATE_DIR), autoescape=True)

_playwright = None
_page = None


def normalize_template(value) -> str:
    """Gemini'nin şablon seçimini doğrular; geçersizse varsayılana düşer."""
    v = str(value or "").strip().upper()
    if v not in TEMPLATES:
        if v:
            print(f"⚠️  Bilinmeyen şablon {value!r}, {DEFAULT_TEMPLATE} kullanılıyor.")
        return DEFAULT_TEMPLATE
    return v


def _data_uri(path: Path) -> str:
    """Görseli base64 data URI olarak gömer — dosya yolu sorunlarını sıfırlar."""
    suffix = path.suffix.lower().lstrip(".") or "png"
    mime = "jpeg" if suffix in ("jpg", "jpeg") else suffix
    return f"data:image/{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def _get_page():
    """Chromium'u tembel başlatır ve süreç boyunca tek sayfayı yeniden kullanır."""
    global _playwright, _page
    if _page is None:
        from playwright.sync_api import sync_playwright
        _playwright = sync_playwright().start()
        browser = _playwright.chromium.launch()
        _page = browser.new_page(viewport={"width": CANVAS_W, "height": CANVAS_H})
        atexit.register(_playwright.stop)
    return _page


def render_image(
    template: str,
    out_path: Path,
    *,
    title: str,
    source: str,
    photo_path: Path,
    badge: str = "",
    logo_data: str | None = None,
) -> Path:
    """Şablonu doldurur, Chromium'da açar, 1080x1350 PNG olarak kaydeder."""
    # Çağıranlar göreli yol veriyor (output/post_final.png); file:// URI'si
    # mutlak yol ister, aksi halde as_uri() ValueError atar.
    out_path = Path(out_path).resolve()

    key = normalize_template(template)
    html = _env.get_template(TEMPLATES[key]).render(
        title=title,
        source=source,
        badge=badge,
        image_data=_data_uri(photo_path),
        logo_data=logo_data,
        fonts_dir=_FONTS_URI,
    )

    html_path = out_path.with_suffix(".html")
    html_path.write_text(html, encoding="utf-8")
    try:
        page = _get_page()
        page.goto(html_path.as_uri())
        page.wait_for_function("document.title === 'fitted'", timeout=15000)
        page.screenshot(path=str(out_path))
    finally:
        html_path.unlink(missing_ok=True)  # ara dosya repoya karışmasın

    return out_path
