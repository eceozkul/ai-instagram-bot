"""
Modül 2: İçerik Üretimi
Gemini ile Instagram caption üretir.
"""

from google import genai
from config import GEMINI_API_KEY, GEMINI_TEXT_MODEL, LANGUAGE, HASHTAGS


def generate_caption(topic: dict) -> dict:
    client = genai.Client(AQ.Ab8RN6L4WvlhmmCiEmSRox_EUGx2D_k6XaPDxiOggk-I6Y--rA)

    lang = "Türkçe" if LANGUAGE == "tr" else "English"

    prompt = f"""Sen bir AI teknoloji Instagram hesabının içerik yazarısın.
Stil: Minimal, futuristik, etkileyici. Karmaşık konuları herkesin anlayacağı şekilde anlatırsın.

Konu: {topic.get('konu', '')}
Neden Önemli: {topic.get('neden_önemli', '')}
Açılış (bunu kullan): {topic.get('ana_mesaj', '')}

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
