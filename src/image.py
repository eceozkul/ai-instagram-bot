"""
Modül 3: Görsel Üretimi
Gemini 2.0 Flash ile futuristik görsel üretir, minimal metin overlay ekler.
"""

import io
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from google.genai import types
from config import GEMINI_IMAGE_MODEL, IMAGE_SIZE
import gemini_client

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


def build_image_prompt(topic: dict) -> str:
    style = (
        "ultra-realistic digital art, futuristic dark background, deep blue and black tones, "
        "subtle neon cyan and purple accent lights, cinematic lighting, photorealistic, "
        "8K resolution, NO text, NO watermark, NO letters, minimalist composition"
    )
    subject = topic.get("gorsel_prompt", "abstract AI neural network visualization")
    return f"{subject}. Style: {style}"


def generate_image(topic: dict) -> Path:
    """Gemini ile görsel üret."""
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
    """1080x1080 kare yap."""
    w, h = image.size
    m = min(w, h)
    left, top = (w - m) // 2, (h - m) // 2
    return image.crop((left, top, left + m, top + m)).resize(
        (IMAGE_SIZE, IMAGE_SIZE), Image.LANCZOS
    )


def add_text_overlay(image_path: Path, topic: dict) -> Path:
    """Futuristik minimal metin overlay ekle."""
    image = Image.open(image_path).convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    w, h = image.size

    # Alt kısım gradient karartma
    for y in range(h // 2, h):
        alpha = int(200 * ((y - h // 2) / (h // 2)))
        draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))

    image = Image.alpha_composite(image, overlay).convert("RGB")
    draw = ImageDraw.Draw(image)

    # Font
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 58)
        font_sub   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
    except:
        font_title = ImageFont.load_default()
        font_sub   = ImageFont.load_default()

    # Başlık — kelime sar
    title = topic.get("konu", "AI Haberleri")
    words = title.split()
    lines, current = [], ""
    for word in words:
        if len(current + word) < 32:
            current += word + " "
        else:
            lines.append(current.strip())
            current = word + " "
    lines.append(current.strip())
    title_display = "\n".join(lines[:3])

    # Neon cyan başlık
    draw.text((55, h - 210), title_display, font=font_title, fill=(0, 220, 255))

    # Kaynak
    source = topic.get("source_name", "AI News")
    draw.text((55, h - 65), f"▸ {source}", font=font_sub, fill=(160, 160, 160))

    # Hesap adı
    draw.text((w - 220, h - 50), "@ai.daily.tr", font=font_sub, fill=(80, 80, 80))

    # Logo — varsa sağ üste ekle
    logo_path = Path(__file__).parent / "logo.png"
    if logo_path.exists():
        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo_size = 90
            logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
            image.paste(logo, (w - logo_size - 30, 30), logo)
        except Exception as e:
            print(f"⚠️  Logo eklenemedi: {e}")

    final_path = OUTPUT_DIR / "post_final.png"
    image.save(final_path, "PNG", quality=95)
    print(f"✓ Final görsel hazır: {final_path}")
    return final_path


def create_post_image(topic: dict) -> Path:
    raw = generate_image(topic)
    return add_text_overlay(raw, topic)


def create_carousel_images(slides: list[dict]) -> list[Path]:
    """Her carousel slaytı için görsel üretir."""
    paths = []
    for i, slide in enumerate(slides):
        print(f"🎨 Slayt {i+1}/{len(slides)} üretiliyor...")
        topic_like = {
            "gorsel_prompt": slide.get("gorsel_prompt", "abstract AI visualization"),
            "konu": slide.get("baslik", ""),
            "source_name": slide.get("source", "AI News")
        }
        raw = generate_image(topic_like)

        # Overlay için slayt başlığını kullan
        image = Image.open(raw).convert("RGBA")
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        w, h = image.size

        for y in range(h // 2, h):
            alpha = int(200 * ((y - h // 2) / (h // 2)))
            draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))

        image = Image.alpha_composite(image, overlay).convert("RGB")
        draw = ImageDraw.Draw(image)

        try:
            font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 52)
            font_sub   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
        except:
            font_title = ImageFont.load_default()
            font_sub   = ImageFont.load_default()

        title = slide.get("baslik", "")
        words = title.split()
        lines, current = [], ""
        for word in words:
            if len(current + word) < 30:
                current += word + " "
            else:
                lines.append(current.strip())
                current = word + " "
        lines.append(current.strip())

        draw.text((55, h - 200), "\n".join(lines[:3]), font=font_title, fill=(0, 220, 255))
        draw.text((55, h - 65), f"▸ {slide.get('source', '')}", font=font_sub, fill=(160, 160, 160))
        draw.text((w - 220, h - 50), "@ai.daily.tr", font=font_sub, fill=(80, 80, 80))

        # Slayt numarası
        draw.text((w - 80, 30), f"{i+1}/{len(slides)}", font=font_sub, fill=(0, 220, 255))

        # Logo
        logo_path = Path(__file__).parent / "logo.png"
        if logo_path.exists():
            try:
                logo = Image.open(logo_path).convert("RGBA")
                logo_size = 70
                logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
                image.paste(logo, (30, 30), logo)
            except Exception as e:
                print(f"⚠️  Logo eklenemedi: {e}")

        slide_path = OUTPUT_DIR / f"carousel_{i+1}.png"
        image.save(slide_path, "PNG", quality=95)
        paths.append(slide_path)

    return paths
