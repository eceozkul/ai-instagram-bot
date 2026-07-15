"""
Gemini API istemcisi
Tüm Gemini çağrıları buradan geçer: retry ve token takibi tek yerde.
"""

import json
import time
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, GEMINI_TEXT_MODEL
import token_tracker

RETRIES = 3
BASE_DELAY = 5  # saniye; denemeler arası bekleme artarak uygulanır

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def get_client():
    """Diğer modüllerin (örn. video üretimi) kullanması için istemciyi döner."""
    return _get_client()


def generate(prompt: str, config=None, model: str = None):
    """Ham Gemini yanıtı döner. Geçici hatalarda tekrar dener."""
    model = model or GEMINI_TEXT_MODEL
    last_err = None
    for attempt in range(1, RETRIES + 1):
        try:
            response = _get_client().models.generate_content(
                model=model, contents=prompt, config=config
            )
            token_tracker.track(response)
            return response
        except Exception as e:
            last_err = e
            token_tracker.track_error(f"{type(e).__name__}: {e}"[:200])
            if attempt < RETRIES:
                wait = BASE_DELAY * attempt
                print(f"  ⚠️  Gemini hatası (deneme {attempt}/{RETRIES}), {wait} sn sonra tekrar: {e}")
                time.sleep(wait)
    raise last_err


def generate_text(prompt: str, model: str = None) -> str:
    """Serbest metin üretir."""
    return generate(prompt, model=model).text.strip()


def generate_json(prompt: str, schema: dict, model: str = None):
    """Şemaya uyan JSON üretir — format API seviyesinde garanti edilir."""
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=schema,
    )
    response = generate(prompt, config=config, model=model)
    return json.loads(response.text)
