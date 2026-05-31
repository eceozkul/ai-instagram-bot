"""
Ana Orkestratör
Tüm modülleri sırayla çalıştırır.
"""

import sys
import json
import traceback
from datetime import datetime
from pathlib import Path

from research import fetch_rss_feeds, score_articles, enrich_topic, enrich_carousel
from content import generate_caption, generate_carousel_caption
from image import create_post_image, create_carousel_images
from post import post_to_instagram, post_carousel_to_instagram
from sheets import load_history, save_to_history, save_log


LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


def log_run(status: str, data: dict):
    log = {
        "timestamp": datetime.now().isoformat(),
        "status": status,
        **data
    }
    log_file = LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.json"
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    print(f"\n📝 Log kaydedildi: {log_file}")


def run():
    print("=" * 50)
    print(f"🤖 AI Instagram Bot başlatıldı — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    try:
        # 1. Haber Toplama
        print("\n[1/4] 📡 Haberler taranıyor...")
        articles = fetch_rss_feeds()
        if not articles:
            print("\n⏭️  Son 4 saatte yeni haber yok, atlanıyor.")
            log_run("skipped", {"reason": "Son 4 saatte yeni haber bulunamadı."})
            save_log("⏭️ haber yok", notes="Son 4 saatte yeni haber bulunamadı.")
            return

        # 2. Puanlama
        print("\n[2/4] 🧠 Haberler puanlanıyor...")
        history = load_history()
        scored = score_articles(articles, history)

        high    = [a for a in scored if a["score"] >= 9]   # 9-10: tek post
        medium  = [a for a in scored if 7 <= a["score"] <= 8]  # 7-8: carousel
        low     = [a for a in scored if a["score"] < 7]

        print(f"\n  🔴 9-10 puan (tek post): {len(high)} haber")
        print(f"  🟡 7-8 puan (carousel): {len(medium)} haber")
        print(f"  ⚪ 5 altı (atlandı): {len(low)} haber")

        if not high and not medium:
            print("\n⏭️  Yeterli önemde haber yok, atlanıyor.")
            log_run("skipped", {"reason": "Tüm haberler 7 puan altında."})
            save_log("⏭️ düşük puan", articles=articles, notes="Hiçbir haber yayın eşiğini geçemedi.")
            return

        # 3. İçerik + Görsel + Post
        if high:
            print(f"\n[3/4] 🔴 Tek post hazırlanıyor (9-10 puan)...")
            topic = enrich_topic(high[0], articles)

            print("\n[4/4] ✍️  Caption yazılıyor...")
            content = generate_caption(topic)

            print("\n[5/4] 🎨 Görsel üretiliyor...")
            image_path = create_post_image(topic)

            print("\n[6/4] 📤 Post atılıyor...")
            post_id = post_to_instagram(image_path, content["caption"])
            save_to_history(topic, post_id, content["caption"])
            save_log("✅ tek post", articles=articles, topic=topic)

            log_run("success", {
                "type": "single",
                "topic": topic.get("konu"),
                "score": high[0]["score"],
                "post_id": post_id
            })

        if medium and len(medium) >= 2:
            print(f"\n[3/4] 🟡 Carousel hazırlanıyor ({len(medium)} haber)...")
            slides = enrich_carousel(medium[:5])

            print("\n[4/4] ✍️  Carousel caption yazılıyor...")
            content = generate_carousel_caption(slides)

            print("\n[5/4] 🎨 Carousel görselleri üretiliyor...")
            image_paths = create_carousel_images(slides)

            print("\n[6/4] 📤 Carousel post atılıyor...")
            carousel_topic = {"konu": "Carousel: AI Haberleri Özeti", "source_name": "Çoklu Kaynak"}
            post_id = post_carousel_to_instagram(image_paths, content["caption"])
            save_to_history(carousel_topic, post_id, content["caption"])
            save_log("✅ carousel", articles=medium, topic=carousel_topic)

            log_run("success", {
                "type": "carousel",
                "slides": len(slides),
                "post_id": post_id
            })

        print("\n✅ Tamamlandı!")

    except Exception as e:
        error_msg = traceback.format_exc()
        print(f"\n❌ Hata: {e}")
        print(error_msg)
        log_run("error", {"error": str(e), "traceback": error_msg})
        save_log("❌ hata", notes=str(e))
        sys.exit(1)


if __name__ == "__main__":
    run()
