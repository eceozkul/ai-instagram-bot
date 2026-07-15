"""
Modül 1: Haber Araştırma
RSS feedlerini tarar, Gemini ile günün en iyi konusunu seçer.
"""

import csv
import io
import feedparser
import requests
from datetime import datetime, timedelta
from config import RSS_FEEDS, LANGUAGE, GOOGLE_SHEET_ID
import gemini_client


def load_feeds_from_sheet() -> list[dict]:
    """Google Sheet'ten RSS feed listesini çeker."""
    url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        reader = csv.DictReader(io.StringIO(response.text))
        feeds = []
        for row in reader:
            name = row.get("name", "").strip()
            url_ = row.get("url", "").strip()
            priority = row.get("priority", "2").strip()
            if name and url_:
                feeds.append({"name": name, "url": url_, "priority": int(priority or 2)})
        if feeds:
            print(f"📋 Google Sheet'ten {len(feeds)} feed yüklendi.")
            return feeds
    except Exception as e:
        print(f"⚠️  Google Sheet okunamadı, varsayılan liste kullanılıyor: {e}")
    return RSS_FEEDS


def fetch_rss_feeds(hours: int = 4) -> list[dict]:
    """RSS feedlerini çeker, son 4 saatteki haberleri döndürür."""
    feeds = load_feeds_from_sheet()
    articles = _fetch(feeds, hours)
    print(f"\nToplam {len(articles)} taze haber bulundu.")
    return articles


def _fetch(feeds: list[dict], hours: int) -> list[dict]:
    """Belirtilen saat aralığındaki haberleri çeker."""
    articles = []
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    for feed_config in feeds:
        try:
            feed = feedparser.parse(feed_config["url"])
            count = 0
            for entry in feed.entries[:15]:
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        published = datetime(*entry.published_parsed[:6])
                    except:
                        pass

                # Zaman filtresi: tarihi bilinmiyorsa dahil et
                if published and published < cutoff:
                    continue

                articles.append({
                    "source": feed_config["name"],
                    "priority": feed_config["priority"],
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", "")[:500],
                    "link": entry.get("link", ""),
                    "published": published.isoformat() if published else "unknown"
                })
                count += 1

            if count:
                print(f"✓ {feed_config['name']}: {count} haber")
        except Exception as e:
            print(f"✗ {feed_config['name']} hatası: {e}")

    return articles


def score_articles(articles: list[dict], history: list[dict] = []) -> list[dict]:
    """Gemini ile her habere 1-10 önem puanı verir."""
    if not articles:
        return []

    articles_text = "\n\n".join([
        f"[{i+1}] Kaynak: {a['source']}\nBaşlık: {a['title']}\nÖzet: {a['summary']}"
        for i, a in enumerate(articles[:25])
    ])

    history_text = ""
    if history:
        recent = history[-20:]
        history_text = "\nDaha önce paylaşılan konular (bunlara benzer haberlerin puanını düşür):\n" + "\n".join([
            f"- {h.get('topic', '')}" for h in recent if h.get('topic')
        ])

    prompt = f"""Aşağıdaki yapay zeka haberlerinin her birine Instagram için önem puanı ver.

Puanlama kriterleri:
- 9-10: Çok büyük haber, sektörü etkiler, herkes konuşur (yeni model çıkışı, büyük duyuru)
- 7-8: Önemli ve ilgi çekici haber, geniş kitleye hitap eder
- 5-6: Orta düzey, niş kitle ilgilenir
- 1-4: Düşük öncelik, teknik detay, akademik makale
{history_text}

Haberler:
{articles_text}

Her haber için numarasını (index, 1'den başlar) ve 1-10 arası puanını (score) döndür."""

    schema = {
        "type": "ARRAY",
        "items": {
            "type": "OBJECT",
            "properties": {
                "index": {"type": "INTEGER"},
                "score": {"type": "INTEGER"},
            },
            "required": ["index", "score"],
        },
    }

    results = gemini_client.generate_json(prompt, schema)
    scores = {}
    for r in results:
        try:
            scores[int(r["index"]) - 1] = max(1, min(10, int(r["score"])))
        except (KeyError, ValueError, TypeError):
            pass

    scored = []
    for i, article in enumerate(articles[:25]):
        score = scores.get(i, 5)
        scored.append({**article, "score": score})
        print(f"  [{score}/10] {article['title'][:60]}")

    return scored


def enrich_topic(article: dict, articles: list[dict]) -> dict:
    """Seçilen haber için Gemini'den detay üretir."""
    lang = "Türkçe" if LANGUAGE == "tr" else "English"

    prompt = f"""Şu yapay zeka haberi için Instagram postu hazırla. Metinler {lang} olsun.

Haber:
Kaynak: {article['source']}
Başlık: {article['title']}
Özet: {article['summary']}

Alanlar:
- konu: tek cümle başlık
- neden_onemli: 2-3 cümle sade dille
- ana_mesaj: çarpıcı açılış cümlesi, emoji ile
- gorsel_prompt: İngilizce futuristik dark neon görsel tarifi (görselde metin olmasın)"""

    schema = {
        "type": "OBJECT",
        "properties": {
            "konu":          {"type": "STRING"},
            "neden_onemli":  {"type": "STRING"},
            "ana_mesaj":     {"type": "STRING"},
            "gorsel_prompt": {"type": "STRING"},
        },
        "required": ["konu", "neden_onemli", "ana_mesaj", "gorsel_prompt"],
    }

    result = gemini_client.generate_json(prompt, schema)
    result["source_link"] = article.get("link", "")
    result["source_name"] = article.get("source", "AI News")
    result["score"] = article.get("score", 0)

    print(f"📰 Konu hazırlandı: {result.get('konu', '?')}")
    return result


def enrich_carousel(articles: list[dict]) -> list[dict]:
    """Carousel için her haberi kısaca zenginleştirir."""
    lang = "Türkçe" if LANGUAGE == "tr" else "English"

    schema = {
        "type": "OBJECT",
        "properties": {
            "baslik":        {"type": "STRING"},
            "aciklama":      {"type": "STRING"},
            "gorsel_prompt": {"type": "STRING"},
        },
        "required": ["baslik", "aciklama", "gorsel_prompt"],
    }

    enriched = []
    for article in articles:
        prompt = f"""Şu yapay zeka haberi için Instagram carousel slaytı hazırla. Metinler {lang} olsun.

Haber:
Başlık: {article['title']}
Özet: {article['summary']}
Kaynak: {article['source']}

Alanlar:
- baslik: kısa çarpıcı başlık (max 8 kelime)
- aciklama: 2 cümle sade açıklama
- gorsel_prompt: İngilizce futuristik dark neon görsel tarifi"""

        slide = gemini_client.generate_json(prompt, schema)
        slide["source"] = article["source"]
        slide["link"] = article["link"]
        slide["score"] = article.get("score", 0)
        enriched.append(slide)

    return enriched
