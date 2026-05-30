"""
Ana Orkestratör
Tüm modülleri sırayla çalıştırır.
"""

import sys
import json
import traceback
from datetime import datetime
from pathlib import Path

from research import fetch_rss_feeds, select_best_topic
from content import generate_caption
from image import create_post_image
from post import post_to_instagram


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
        print("\n[1/4] 📡 Haberler taranıyor...")
        articles = fetch_rss_feeds()
        if not articles:
            raise ValueError("Hiç haber bulunamadı.")

        print("\n[2/4] 🧠 Konu seçiliyor...")
        topic = select_best_topic(articles)

        print("\n[3/4] ✍️  Caption yazılıyor...")
        content = generate_caption(topic)

        print("\n[4/4] 🎨 Görsel üretiliyor...")
        image_path = create_post_image(topic)

        print("\n[5/4] 📤 Post atılıyor...")
        post_id = post_to_instagram(image_path, content["caption"])

        log_run("success", {
            "topic": topic.get("konu"),
            "post_id": post_id,
            "caption_length": len(content["caption"])
        })

        print("\n✅ Tamamlandı!")

    except Exception as e:
        error_msg = traceback.format_exc()
        print(f"\n❌ Hata: {e}")
        print(error_msg)
        log_run("error", {"error": str(e), "traceback": error_msg})
        sys.exit(1)


if __name__ == "__main__":
    run()
