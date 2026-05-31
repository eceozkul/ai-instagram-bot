"""
Modül 2: İçerik Üretimi
Gemini ile Instagram caption üretir.
"""

from google import genai
from config import GEMINI_API_KEY, GEMINI_TEXT_MODEL, LANGUAGE, HASHTAGS


def generate_caption(topic: dict) -> dict:
    client = genai.Client(api_key=GEMINI_API_KEY)

    lang = "Türkçe" if LANGUAGE == "tr" else "English"

    revize = f"\n\nRevize talebi: {topic['revize_notu']}" if topic.get("revize_notu") else ""

    prompt = f"""Sen bir AI teknoloji Instagram hesabının içerik yazarısın.
Stil: Minimal, futuristik, etkileyici. Karmaşık konuları herkesin anlayacağı şekilde anlatırsın.

Konu: {topic.get('konu', '')}
Neden Önemli: {topic.get('neden_önemli', '')}
Açılış (bunu kullan): {topic.get('ana_mesaj', '')}{revize}

{lang} dilinde Instagram caption yaz:
- İlk satır: verilen açılış cümlesini kullan
- 2-3 kısa paragraf (her biri max 2 cümle)
- Teknik jargon yok
- Son satır: CTA (kaydet, takip et veya yorum yap)
- Max 150 kelime

Sadece caption metnini yaz, başka açıklama ekleme."""

    response = client.models.generate_content(
        model=GEMINI_TEXT_MODEL,
        contents=prompt
    )

    caption_text = response.text.strip()
    hashtag_str = " ".join(HASHTAGS[:10])
    full_caption = f"{caption_text}\n\n{hashtag_str}"

    print(f"✓ Caption üretildi ({len(caption_text)} karakter)")
    return {"caption": full_caption, "caption_text": caption_text}


def generate_carousel_caption(slides: list[dict]) -> dict:
    """Carousel post için caption üretir."""
    client = genai.Client(api_key=GEMINI_API_KEY)
    lang = "Türkçe" if LANGUAGE == "tr" else "English"

    titles = "\n".join([f"- {s.get('baslik', '')}" for s in slides])

    prompt = f"""Sen bir AI teknoloji Instagram hesabının içerik yazarısın.
Bu bir carousel (kaydırmalı) post. Birden fazla haberi özetliyor.

Haberler:
{titles}

{lang} dilinde carousel caption yaz:
- İlk satır: "🔄 Son dakika AI haberleri:" şeklinde başla, süre yazma
- Her haber için 1 satır emoji + kısa özet
- Son satır: "Kaydet, kaçırma! 🔖"
- Max 150 kelime
- Kesinlikle ** veya * gibi markdown işareti kullanma, düz metin yaz

Sadece caption metnini yaz."""

    response = client.models.generate_content(
        model=GEMINI_TEXT_MODEL,
        contents=prompt
    )

    caption_text = response.text.strip()
    hashtag_str = " ".join(HASHTAGS[:10])
    full_caption = f"{caption_text}\n\n{hashtag_str}"

    print(f"✓ Carousel caption üretildi ({len(caption_text)} karakter)")
    return {"caption": full_caption, "caption_text": caption_text}
