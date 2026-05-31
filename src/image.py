"""
Modül 3: Görsel Üretimi
Gemini 2.0 Flash ile futuristik görsel üretir, minimal metin overlay ekler.
"""

import io
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, GEMINI_IMAGE_MODEL, IMAGE_SIZE

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
    """Imagen 3 ile görsel üret."""
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = build_image_prompt(topic)

    print(f"🎨 Görsel üretiliyor...")

    response = client.models.generate_images(
        model=GEMINI_IMAGE_MODEL,
        prompt=prompt,
        config=types.GenerateImagesConfig(
            number_of_images=1,
            aspect_ratio="1:1",
        )
    )

    image = response.generated_images[0].image
    img = Image.open(io.BytesIO(image.image_bytes))
    img = crop_to_square(img)
    raw_path = OUTPUT_DIR / "post_raw.png"
    img.save(raw_path, "PNG")
    print(f"✓ Ham görsel kaydedildi")
    return raw_path


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

    final_path = OUTPUT_DIR / "post_final.png"
    image.save(final_path, "PNG", quality=95)
    print(f"✓ Final görsel hazır: {final_path}")
    return final_path


def create_post_image(topic: dict) -> Path:
    raw = generate_image(topic)
    return add_text_overlay(raw, topic)
