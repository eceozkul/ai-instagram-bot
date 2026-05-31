"""
Telegram Onay Modülü
Hazırlanan içeriği Telegram'a gönderir, onay bekler.
"""

import os
import time
import requests
from pathlib import Path

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def send_for_approval(image_path: Path, caption: str, topic: dict, post_type: str = "single") -> bool:
    """
    Görseli ve caption'ı Telegram'a gönderir.
    Kullanıcı 'Onayla' basarsa True, 'Atla' basarsa False döner.
    30 dakika içinde yanıt gelmezse False döner.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️  Telegram ayarları eksik, otomatik onaylanıyor.")
        return True

    type_label = "🔴 TEK POST" if post_type == "single" else "🟡 CAROUSEL"
    score = topic.get("score", "?")
    konu = topic.get("konu", "")
    source = topic.get("source_name", "")

    info_text = (
        f"{type_label} | Puan: {score}/10\n\n"
        f"📰 {konu}\n"
        f"📌 Kaynak: {source}\n\n"
        f"Caption önizleme:\n{caption[:300]}..."
    )

    # Önce bilgi mesajı gönder
    _send_message(info_text)

    # Sonra görseli onayla/atla butonlarıyla gönder
    message_id = _send_photo_with_buttons(image_path)
    if not message_id:
        print("⚠️  Telegram görseli gönderilemedi, otomatik onaylanıyor.")
        return True

    print(f"📱 Telegram'a gönderildi. Onay bekleniyor (max 30 dk)...")

    # Callback bekle
    return _wait_for_callback(message_id, timeout=1800)


def send_carousel_for_approval(image_paths: list[Path], caption: str, slides: list[dict]) -> bool:
    """Carousel için ilk görseli preview olarak gönderir."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️  Telegram ayarları eksik, otomatik onaylanıyor.")
        return True

    titles = "\n".join([f"• {s.get('baslik', '')}" for s in slides])
    info_text = (
        f"🟡 CAROUSEL | {len(slides)} slayt\n\n"
        f"Haberler:\n{titles}\n\n"
        f"Caption önizleme:\n{caption[:300]}..."
    )

    _send_message(info_text)
    message_id = _send_photo_with_buttons(image_paths[0])
    if not message_id:
        return True

    print(f"📱 Carousel Telegram'a gönderildi. Onay bekleniyor (max 30 dk)...")
    return _wait_for_callback(message_id, timeout=1800)


def _send_message(text: str):
    requests.post(f"{BASE_URL}/sendMessage", json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    })


def _send_photo_with_buttons(image_path: Path) -> int | None:
    """Görseli inline butonlarla gönderir, message_id döner."""
    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Onayla", "callback_data": "approve"},
            {"text": "❌ Atla",   "callback_data": "skip"}
        ]]
    }
    with open(image_path, "rb") as f:
        response = requests.post(
            f"{BASE_URL}/sendPhoto",
            data={
                "chat_id": TELEGRAM_CHAT_ID,
                "reply_markup": str(keyboard).replace("'", '"')
            },
            files={"photo": f}
        )

    if response.ok:
        return response.json()["result"]["message_id"]
    print(f"⚠️  Telegram foto gönderilemedi: {response.text}")
    return None


def _wait_for_callback(message_id: int, timeout: int = 1800) -> bool:
    """Telegram callback'i polling ile bekler."""
    offset = None
    deadline = time.time() + timeout
    poll_interval = 5

    while time.time() < deadline:
        params = {"timeout": poll_interval, "allowed_updates": ["callback_query"]}
        if offset:
            params["offset"] = offset

        try:
            resp = requests.get(f"{BASE_URL}/getUpdates", params=params, timeout=poll_interval + 5)
            updates = resp.json().get("result", [])
        except Exception as e:
            print(f"⚠️  Telegram polling hatası: {e}")
            time.sleep(5)
            continue

        for update in updates:
            offset = update["update_id"] + 1
            cb = update.get("callback_query")
            if not cb:
                continue

            # Callback'i onayla
            requests.post(f"{BASE_URL}/answerCallbackQuery", json={
                "callback_query_id": cb["id"]
            })

            data = cb.get("data")
            if data == "approve":
                _send_message("✅ Onaylandı! Post atılıyor...")
                print("✅ Telegram onayı alındı.")
                return True
            elif data == "skip":
                _send_message("❌ Atlandı.")
                print("❌ Telegram'dan atla komutu geldi.")
                return False

    # Timeout
    _send_message("⏰ 30 dakika içinde yanıt gelmedi, post atlanıyor.")
    print("⏰ Telegram onayı zaman aşımına uğradı.")
    return False
