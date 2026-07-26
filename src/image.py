"""
Modül 3: Görsel Üretimi
General AI News marka kimliği: temiz beyaz kompozisyon, asimetrik yerleşim
(sağ 1/3 fotoğraf, sol 2/3 beyaz alan + metin), lacivert/lime aksanlar.
"""

import io
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from google.genai import types
from config import GEMINI_IMAGE_MODEL, IMAGE_SIZE
import gemini_client

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)
FONTS_DIR = Path(__file__).parent / "fonts"

# Marka paleti (logodan)
NAVY       = (13, 27, 79)      # #0D1B4F — logo zemini, başlık metni
LIME       = (176, 230, 90)    # #B0E65A — logo aksanı
WHITE      = (255, 255, 255)
LIGHT_GRAY = (245, 246, 248)   # beyaz alan için hafif ton farkı
GRAY_TEXT  = (110, 118, 140)   # kaynak/alt bilgi metni


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = FONTS_DIR / name
    try:
        return ImageFont.truetype(str(path), size)
    except Exception:
        return ImageFont.load_default()


# logo.png tam lockup'tır (ikon + "General AI News" yazısı yan yana).
# Küçük boyutlarda yazı okunmaz hale geldiği için sadece ikon kısmını kırpıp kullanıyoruz.
_LOGO_ICON_CROP_RATIO = (0.13, 0.08, 0.565, 0.75)  # (left, top, right, bottom)
_logo_icon_cache = None


def _load_logo_icon() -> Image.Image | None:
    """logo.png'den sadece dairesel ikonu kırpıp döner (yoksa None)."""
    global _logo_icon_cache
    if _logo_icon_cache is not None:
        return _logo_icon_cache

    logo_path = Path(__file__).parent / "logo.png"
    if not logo_path.exists():
        return None

    try:
        logo = Image.open(logo_path).convert("RGBA")
        w, h = logo.size
        l, t, r, b = _LOGO_ICON_CROP_RATIO
        _logo_icon_cache = logo.crop((int(w * l), int(h * t), int(w * r), int(h * b)))
        return _logo_icon_cache
    except Exception as e:
        print(f"⚠️  Logo yüklenemedi: {e}")
        return None


def build_image_prompt(topic: dict) -> str:
    """General AI News kurumsal fotoğraf stili — sadece sağ 1/3'te kullanılacak sahne."""
    subject = topic.get("gorsel_prompt", "abstract AI technology visualization")
    style = (
        "professional stock photography style, clean bright white or very light background, "
        "realistic natural daylight, high-end editorial photography quality, NOT abstract digital art, "
        "the scene includes one clear accent of lime green (#B0E65A) light, glow, plastic or object "
        "somewhere in frame, otherwise neutral white/light gray tones, NO dark navy background, "
        "NO text, NO watermark, NO letters, NO logos, clean minimal composition with breathing room"
    )
    return f"{subject}. Style: {style}"


def generate_image(topic: dict) -> Path:
    """Gemini ile sahne fotoğrafı üret (sadece sağ panelde kullanılacak)."""
    prompt = build_image_prompt(topic)

    print(f"🎨 Görsel üretiliyor...")

    response = gemini_client.generate(
        prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"]
        ),
        model=GEMINI_IMAGE_MODEL,
    )

    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            img = Image.open(io.BytesIO(part.inline_data.data))
            img = crop_to_square(img)
            raw_path = OUTPUT_DIR / "post_raw.png"
            img.save(raw_path, "PNG")
            print(f"✓ Ham görsel kaydedildi")
            return raw_path

    raise ValueError("Gemini görsel üretemedi.")


def crop_to_square(image: Image.Image) -> Image.Image:
    """1080x1080 kare yap (Gemini kaynak görselini normalize etmek için)."""
    w, h = image.size
    m = min(w, h)
    left, top = (w - m) // 2, (h - m) // 2
    return image.crop((left, top, left + m, top + m)).resize(
        (IMAGE_SIZE, IMAGE_SIZE), Image.LANCZOS
    )


def _cover_resize(image: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """CSS 'object-fit: cover' gibi — oranı bozmadan hedef kutuyu doldurup taşanı kırpar."""
    src_w, src_h = image.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w, new_h = round(src_w * scale), round(src_h * scale)
    resized = image.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    """Piksel genişliğine göre kelime sarma."""
    words = text.split()
    lines, current = [], ""
    for word in words:
        trial = f"{current}{word} "
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current.strip())
            current = word + " "
    if current:
        lines.append(current.strip())
    return lines


# Başlık tipografisi — 54px standart boyut, sığmazsa kademeli 42px'e kadar küçülür.
# Tavan bilerek 54'te tutuluyor: daha büyük punto kısa başlıklarda devreye girip
# akışta postlar arası boyut farkı yaratıyordu, hesap genelinde uyum bozuluyordu.
_TITLE_SIZE_MAX  = 54
_TITLE_SIZE_MIN  = 42
_TITLE_LINE_RATIO = 1.26   # satır yüksekliği / font boyutu (54 → 68)
_TITLE_MAX_LINES  = 8      # estetik üst sınır; bunun üstünde font küçülür.
                           # 8 seçildi çünkü tipik haber başlığı 54px'te en fazla
                           # bu kadar sürüyor — böylece post ve carousel aynı puntoda kalıyor.


def _fit_title(
    title: str,
    max_width: int,
    available_h: int,
    draw: ImageDraw.ImageDraw,
) -> tuple[ImageFont.FreeTypeFont, list[str], int]:
    """
    Başlığı ayrılan kutuya sığdırır: 62px'ten başlayıp sığana kadar fontu küçültür.
    Önceden satır sayısı 4'te sabit kesiliyordu ve uzun başlıkların sonu sessizce
    kaybolup cümle yarıda kalıyordu. En küçük fontta bile sığmazsa "…" ile kısaltır.
    Döner: (font, satırlar, satır yüksekliği)
    """
    font = line_height = lines = None
    for size in range(_TITLE_SIZE_MAX, _TITLE_SIZE_MIN - 1, -2):
        font = _font("Montserrat-Bold.ttf", size)
        line_height = round(size * _TITLE_LINE_RATIO)
        lines = _wrap_text(title, font, max_width, draw)
        # Küçültme kararı estetik sınıra göre verilir; asıl sınır kutunun yüksekliği.
        if len(lines) <= max(1, min(_TITLE_MAX_LINES, available_h // line_height)):
            return font, lines, line_height

    # En küçük fonta gelindi: artık estetik sınırı bırak, kutuya sığdığı kadar göster
    hard_max = max(1, available_h // line_height)
    if len(lines) <= hard_max:
        return font, lines, line_height

    # Kutuya da sığmıyor: kes ve üç nokta koy
    lines = lines[:hard_max]
    last = lines[-1].rstrip(" ,;:") + "…"
    while len(last) > 1 and draw.textlength(last, font=font) > max_width:
        last = last[:-2].rstrip(" ,;:") + "…"
    lines[-1] = last
    return font, lines, line_height


def _compose_branded_image(photo: Image.Image, title: str, source: str, badge: str = "") -> Image.Image:
    """
    Asimetrik marka kompozisyonu: sol ~62% beyaz alan + metin, sağ ~38% fotoğraf.
    Kanvas 4:5 (1080x1350) — Instagram feed'in önerdiği standart dikey oran;
    kare (1:1) postlar akışta bazı görünümlerde otomatik/asimetrik kırpılabiliyor,
    4:5 ise tam boyutuyla, kırpılmadan gösteriliyor.
    photo: Gemini'nin ürettiği kare görsel (sağ panele oranı bozulmadan kırpılıp yerleştirilir).
    """
    W, H = IMAGE_SIZE, int(IMAGE_SIZE * 5 / 4)
    canvas = Image.new("RGB", (W, H), WHITE)
    draw = ImageDraw.Draw(canvas)

    # Sağ panel: fotoğraf (oranı bozmadan 'cover' ile doldurulur, gerip bozmaz)
    panel_w = int(W * 0.38)
    photo_resized = _cover_resize(photo, panel_w, H)
    canvas.paste(photo_resized, (W - panel_w, 0))

    # Panel ile beyaz alan arasında ince lime çizgi
    draw.rectangle([(W - panel_w - 4, 0), (W - panel_w, H)], fill=LIME)

    # Sol 2/3: beyaz/açık gri metin alanı
    text_area_w = W - panel_w - 4
    margin = 70
    max_text_width = text_area_w - margin * 2

    font_sub   = _font("Montserrat-Regular.ttf", 30)
    font_badge = _font("Montserrat-SemiBold.ttf", 24)

    # Üstte küçük rozet (opsiyonel — carousel slayt no vb.)
    y = 90
    if badge:
        bw = draw.textlength(badge, font=font_badge) + 40
        draw.rounded_rectangle([(margin, y), (margin + bw, y + 46)], radius=23, fill=LIME)
        draw.text((margin + 20, y + 10), badge, font=font_badge, fill=NAVY)
        y += 90

    # Başlık — dikey ortalamaya yakın, lacivert.
    # Alt sınır: logo ikonunun üstü (H - 170) eksi nefes payı.
    title_bottom_limit = H - 210
    font_title, lines, line_height = _fit_title(
        title, max_text_width, title_bottom_limit - y, draw
    )
    title_h = len(lines) * line_height
    title_y = max(y, (H - title_h) // 2 - 40)
    title_y = min(title_y, title_bottom_limit - title_h)
    for line in lines:
        draw.text((margin, title_y), line, font=font_title, fill=NAVY)
        title_y += line_height

    # Alt bilgi — kaynak
    draw.text((margin, H - 90), f"— {source}", font=font_sub, fill=GRAY_TEXT)

    # Logo ikonu — kaynak metninin hemen üstünde, sol alt köşe
    icon = _load_logo_icon()
    if icon is not None:
        icon_size = 64
        icon_resized = icon.resize((icon_size, icon_size), Image.LANCZOS)
        canvas.paste(icon_resized, (margin, H - 170), icon_resized)

    return canvas


def create_post_image(topic: dict) -> Path:
    raw_path = generate_image(topic)
    photo = Image.open(raw_path).convert("RGB")

    final = _compose_branded_image(
        photo=photo,
        title=topic.get("konu", "AI Haberleri"),
        source=topic.get("source_name", "AI News"),
    )

    final_path = OUTPUT_DIR / "post_final.png"
    final.save(final_path, "PNG", quality=95)
    print(f"✓ Final görsel hazır: {final_path}")
    return final_path


def create_carousel_images(slides: list[dict]) -> list[Path]:
    """Her carousel slaytı için marka kimliğine uygun görsel üretir."""
    paths = []
    for i, slide in enumerate(slides):
        print(f"🎨 Slayt {i+1}/{len(slides)} üretiliyor...")
        topic_like = {
            "gorsel_prompt": slide.get("gorsel_prompt", "abstract AI visualization"),
        }
        raw_path = generate_image(topic_like)
        photo = Image.open(raw_path).convert("RGB")

        final = _compose_branded_image(
            photo=photo,
            title=slide.get("baslik", ""),
            source=slide.get("source", "AI News"),
            badge=f"{i+1}/{len(slides)}",
        )

        slide_path = OUTPUT_DIR / f"carousel_{i+1}.png"
        final.save(slide_path, "PNG", quality=95)
        paths.append(slide_path)

    return paths
