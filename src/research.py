"""
Modül 1: Haber Araştırma
RSS feedlerini tarar, Gemini ile günün en iyi konusunu seçer.
"""

import feedparser
from google import genai
from datetime import datetime, timedelta
from config import GEMINI_API_KEY, GEMINI_TEXT_MODEL, RSS_FEEDS, LANGUAGE


def fetch_rss_feeds() -> list[dict]:
    """RSS feedlerini çeker, tarih filtresi olmadan tüm haberleri döndürür."""
    articles = []

    for feed_config in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_config["url"])
            count = 0
            for entry in feed.entries[:10]:
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        published = datetime(*entry.published_parsed[:6])
                    except:
                        pass

                articles.append({
                    "source": feed_config["name"],
                    "priority": feed_config["priority"],
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", "")[:500],
                    "link": entry.get("link", ""),
                    "published": published.isoformat() if published else "unknown"
                })
                count += 1

            print(f"✓ {feed_config['name']}: {count} haber")
        except Exception as e:
            print(f"✗ {feed_config['name']} hatası: {e}")

    print(f"\nToplam {len(articles)} haber bulundu.")
    return articles


def select_best_topic(articles: list[dict]) -> dict:
    """Gemini ile en iyi konuyu seçer."""
    if not articles:
        raise ValueError("Haber bulunamadı.")

    client = genai.Client(api_key=GEMINI_API_KEY)

    articles_text = "\n\n".join([
        f"[{i+1}] Kaynak: {a['source']}\nBaşlık: {a['title']}\nÖzet: {a['summary']}"
        for i, a in enumerate(articles[:20])
    ])

    lang = "Türkçe" if LANGUAGE == "tr" else "English"

    prompt = f"""Aşağıdaki yapay zeka haberlerinden Instagram için en uygun konuyu seç.

Seçim kriterleri:
- Geniş kitleye hitap etmeli
- Güncel ve önemli olmalı
- Görsel anlatıma uygun olmalı
- İlgi çekici olmalı

Haberler:
{articles_text}

Seçtiğin haber için şunları {lang} olarak ver.
Her satırı TAM OLARAK bu formatla yaz:

KONU: tek cümle başlık
NEDEN_ÖNEMLI: 2-3 cümle sade dille
ANA_MESAJ: çarpıcı açılış cümlesi emoji ile
GORSEL_PROMPT: İngilizce futuristik dark neon görsel tarifi sadece görsel metin yok
KAYNAK_BASLIK: orijinal haber başlığı"""

    response = client.models.generate_content(
        model=GEMINI_TEXT_MODEL,
        contents=prompt
    )

    return parse_topic_response(response.text, articles)


def parse_topic_response(raw: str, articles: list[dict]) -> dict:
    result = {}
    fields = ["KONU", "NEDEN_ÖNEMLI", "ANA_MESAJ", "GORSEL_PROMPT", "KAYNAK_BASLIK"]

    for field in fields:
        tag = f"{field}:"
        if tag in raw:
            start = raw.index(tag) + len(tag)
            next_positions = [raw.index(f"{f}:") for f in fields
                              if f"{f}:" in raw and raw.index(f"{f}:") > start]
            end = min(next_positions) if next_positions else len(raw)
            result[field.lower()] = raw[start:end].strip()

    for article in articles:
        if article["title"][:30] in result.get("kaynak_baslik", ""):
            result["source_link"] = article["link"]
            result["source_name"] = article["source"]
            break

    if "source_name" not in result:
        result["source_name"] = articles[0]["source"] if articles else "AI News"

    print(f"📰 Seçilen konu: {result.get('konu', '?')}")
    return result
