"""
Modül 3: Görsel Üretimi
Gemini'den sahne fotoğrafı alır, HTML/CSS şablonuyla (renderer.py) marka
görseline dönüştürür. Şablon seçimini Gemini yapar (topic["sablon"]: A/B/C).
"""

import io
import base64
from pathlib import Path
from PIL import Image
from google.genai import types
from config import GEMINI_IMAGE_MODEL
import gemini_client
import renderer

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# Ortak fotoğraf stili — hangi şablon olursa olsun geçerli
_STYLE_COMMON = (
    "professional stock photography style, realistic natural daylight, "
    "high-end editorial photography quality, NOT abstract digital art, "
    "one clear accent of lime green (#B0E65A) light, glow, plastic or object "
    "somewhere in frame, NO text, NO watermark, NO letters, NO logos"
)

# Şablona göre kompozisyon farkı: A dar dikey panelde, B geniş üst şeritte,
# C tam ekran arka planda kullanılıyor
_STYLE_BY_TEMPLATE = {
    "A": "clean bright white or very light background, neutral white/light gray "
         "tones, NO dark navy background, minimal composition with breathing room",
    "B": "wide horizontal composition with the subject centered, clean bright "
         "scene, works when cropped to a wide banner",
    "C": "cinematic wide atmospheric scene with depth, slightly moody but still "
         "bright enough to sit under a dark navy gradient overlay",
}


def build_image_prompt(topic: dict, template: str) -> str:
    subject = topic.get("gorsel_prompt", "abstract AI technology visualization")
    return f"{subject}. Style: {_STYLE_COMMON}, {_STYLE_BY_TEMPLATE[template]}"


def generate_image(topic: dict, template: str = "A") -> Path:
    """Gemini ile şablona uygun sahne fotoğrafı üretir."""
    prompt = build_image_prompt(topic, template)

    print(f"🎨 Görsel üretiliyor (şablon {template})...")

    response = gemini_client.generate(
        prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"]
        ),
        model=GEMINI_IMAGE_MODEL,
    )

    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            img = Image.open(io.BytesIO(part.inline_data.data)).convert("RGB")
            raw_path = OUTPUT_DIR / "post_raw.png"
            img.save(raw_path, "PNG")  # kırpma yok — şablon CSS'i object-fit: cover ile kırpar
            print(f"✓ Ham görsel kaydedildi")
            return raw_path

    raise ValueError("Gemini görsel üretemedi.")


# logo.png tam lockup'tır (ikon + "General AI News" yazısı yan yana).
# Küçük boyutlarda yazı okunmaz hale geldiği için sadece ikon kısmını kırpıp kullanıyoruz.
_LOGO_ICON_CROP_RATIO = (0.13, 0.08, 0.565, 0.75)  # (left, top, right, bottom)
_logo_data_cache = None


def _logo_data_uri() -> str | None:
    """logo.png'den dairesel ikonu kırpıp base64 data URI olarak döner (yoksa None)."""
    global _logo_data_cache
    if _logo_data_cache is not None:
        return _logo_data_cache

    logo_path = Path(__file__).parent / "logo.png"
    if not logo_path.exists():
        return None

    try:
        logo = Image.open(logo_path).convert("RGBA")
        w, h = logo.size
        l, t, r, b = _LOGO_ICON_CROP_RATIO
        icon = logo.crop((int(w * l), int(h * t), int(w * r), int(h * b)))
        buf = io.BytesIO()
        icon.save(buf, "PNG")
        _logo_data_cache = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
        return _logo_data_cache
    except Exception as e:
        print(f"⚠️  Logo yüklenemedi: {e}")
        return None


def create_post_image(topic: dict) -> Path:
    template = renderer.normalize_template(topic.get("sablon"))
    raw_path = generate_image(topic, template)

    final_path = renderer.render_image(
        template,
        OUTPUT_DIR / "post_final.png",
        title=topic.get("konu", "AI Haberleri"),
        source=topic.get("source_name", "AI News"),
        photo_path=raw_path,
        logo_data=_logo_data_uri(),
    )
    print(f"✓ Final görsel hazır: {final_path}")
    return final_path


def create_carousel_images(slides: list[dict]) -> list[Path]:
    """Her carousel slaytı için Gemini'nin seçtiği şablonla görsel üretir."""
    paths = []
    for i, slide in enumerate(slides):
        print(f"🎨 Slayt {i+1}/{len(slides)} üretiliyor...")
        template = renderer.normalize_template(slide.get("sablon"))
        raw_path = generate_image(
            {"gorsel_prompt": slide.get("gorsel_prompt", "abstract AI visualization")},
            template,
        )

        path = renderer.render_image(
            template,
            OUTPUT_DIR / f"carousel_{i+1}.png",
            title=slide.get("baslik", ""),
            source=slide.get("source", "AI News"),
            photo_path=raw_path,
            badge=f"{i+1}/{len(slides)}",
            logo_data=_logo_data_uri(),
        )
        paths.append(path)

    return paths
