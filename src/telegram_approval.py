"""
Telegram Onay Modülü
Hazırlanan içeriği Telegram'a gönderir, onay/red/revize bekler.
"""

import os
import time
import requests
from pathlib import Path

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def check_commands():
    """
    Telegram'dan bekleyen /pause veya /resume komutlarını kontrol eder.
    Sheet'teki bot_status'u günceller.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    try:
        from sheets import set_bot_status
        resp = requests.get(f"{BASE_URL}/getUpdates", params={"allowed_updates": ["message"]}, timeout=10)
        updates = resp.json().get("result", [])

        if not updates:
            return

        last_offset = None
        for update in updates:
            last_offset = update["update_id"] + 1
            msg = update.get("message", {})
            text = msg.get("text", "").strip().lower()

            if text == "/pause":
                set_bot_status("paused")
                _send_message("⏸️ Bot duraklatıldı. Devam ettirmek için /resume yaz.")
                print("⏸️ Bot pause edildi.")
                from sheets import save_log
                save_log("⏸️ pause", notes="Telegram'dan /pause komutu alındı.")
            elif text == "/resume":
                set_bot_status("active")
                _send_message("▶️ Bot yeniden aktif!")
                print("▶️ Bot resume edildi.")
                from sheets import save_log
                save_log("▶️ resume", notes="Telegram'dan /resume komutu alındı.")
            elif text == "/status":
                from sheets import get_bot_status
                status = get_bot_status()
                _send_message(f"Bot durumu: {'▶️ Aktif' if status == 'active' else '⏸️ Duraklatılmış'}")

        # Mesajları okundu olarak işaretle — bir sonraki çalışmada tekrar işlenmez
        if last_offset:
            requests.get(f"{BASE_URL}/getUpdates", params={"offset": last_offset}, timeout=5)

    except Exception as e:
        print(f"⚠️  Komut kontrolü hatası: {e}")


def send_for_approval(image_path: Path, caption: str, topic: dict, post_type: str = "single") -> tuple[bool, dict]:
    """
    Görseli ve caption'ı Telegram'a gönderir.
    Döner: (onaylandı_mı, revize_talimatları)
    revize_talimatları = {"caption": "...", "image": "..."} veya {}
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️  Telegram ayarları eksik, otomatik onaylanıyor.")
        return True, {}

    type_label = "🔴 TEK POST" if post_type == "single" else "🟡 CAROUSEL"
    score = topic.get("score", "?")
    konu = topic.get("konu", "")
    source = topic.get("source_name", "")

    info_text = (
        f"{type_label} | Puan: {score}/10\n\n"
        f"📰 {konu}\n"
        f"📌 Kaynak: {source}\n\n"
        f"Caption:\n{caption[:400]}"
    )
    _send_message(info_text)

    message_id = _send_photo_with_buttons(image_path)
    if not message_id:
        print("⚠️  Telegram görseli gönderilemedi, otomatik onaylanıyor.")
        return True, {}

    print(f"📱 Telegram'a gönderildi. Onay bekleniyor (max 1 saat)...")
    return _wait_for_callback(message_id, timeout=3600)


def send_carousel_for_approval(image_paths: list[Path], caption: str, slides: list[dict]) -> tuple[bool, dict]:
    """Carousel için tüm slaytları gönderir, son slayta onay butonu ekler."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️  Telegram ayarları eksik, otomatik onaylanıyor.")
        return True, {}

    titles = "\n".join([f"• {s.get('baslik', '')}" for s in slides])
    info_text = (
        f"🟡 CAROUSEL | {len(slides)} slayt\n\n"
        f"Haberler:\n{titles}\n\n"
        f"Caption:\n{caption[:400]}"
    )
    _send_message(info_text)

    message_id = None
    for i, path in enumerate(image_paths):
        if i == len(image_paths) - 1:
            message_id = _send_photo_with_buttons(path)
        else:
            _send_photo(path)

    if not message_id:
        return True, {}

    print(f"📱 Carousel ({len(image_paths)} slayt) Telegram'a gönderildi. Onay bekleniyor (max 1 saat)...")
    return _wait_for_callback(message_id, timeout=3600)


def notify_error(text: str):
    """Hata durumunda kullanıcıya Telegram'dan haber verir. Asla exception fırlatmaz."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        requests.post(f"{BASE_URL}/sendMessage", json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text[:4000],
        }, timeout=10)
    except Exception:
        pass


def _send_message(text: str):
    requests.post(f"{BASE_URL}/sendMessage", json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    })


def _send_photo(image_path: Path):
    """Görseli butonsuz gönderir."""
    with open(image_path, "rb") as f:
        requests.post(
            f"{BASE_URL}/sendPhoto",
            data={"chat_id": TELEGRAM_CHAT_ID},
            files={"photo": f}
        )


def _send_photo_with_buttons(image_path: Path) -> int | None:
    """Görseli inline butonlarla gönderir, message_id döner."""
    import json
    keyboard = json.dumps({
        "inline_keyboard": [[
            {"text": "✅ Onayla",     "callback_data": "approve"},
            {"text": "✏️ Revize Et", "callback_data": "revise"},
            {"text": "❌ Atla",       "callback_data": "skip"}
        ]]
    })
    with open(image_path, "rb") as f:
        response = requests.post(
            f"{BASE_URL}/sendPhoto",
            data={
                "chat_id": TELEGRAM_CHAT_ID,
                "reply_markup": keyboard
            },
            files={"photo": f}
        )

    if response.ok:
        return response.json()["result"]["message_id"]
    print(f"⚠️  Telegram foto gönderilemedi: {response.text}")
    return None


def _wait_for_callback(message_id: int, timeout: int = 1800) -> tuple[bool, dict]:
    """
    Telegram callback'i polling ile bekler.
    Döner: (onaylandı_mı, revize_talimatları)
    """
    offset = None
    deadline = time.time() + timeout
    poll_interval = 5

    while time.time() < deadline:
        params = {"timeout": poll_interval, "allowed_updates": ["callback_query", "message"]}
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

            # Callback (buton)
            cb = update.get("callback_query")
            if cb:
                requests.post(f"{BASE_URL}/answerCallbackQuery", json={"callback_query_id": cb["id"]})
                data = cb.get("data")

                if data == "approve":
                    _send_message("✅ Onaylandı! Post atılıyor...")
                    print("✅ Telegram onayı alındı.")
                    return True, {}

                elif data == "skip":
                    _send_message("❌ Atlandı.")
                    print("❌ Telegram'dan atla komutu geldi.")
                    return True, {}

                elif data == "revise":
                    _send_message(
                        "✏️ Neyi revize etmek istiyorsun? Yazarak belirt:\n\n"
                        "Sadece caption için: <b>caption: isteğin</b>\n"
                        "Sadece görsel için: <b>görsel: isteğin</b>\n"
                        "İkisi için: <b>caption: ... görsel: ...</b>"
                    )
                    print("✏️ Revize talebi alındı, kullanıcı talimat yazıyor...")
                    # Kullanıcının mesajını bekle
                    revize = _wait_for_revise_message(offset, deadline)
                    return False, revize

    _send_message("⏰ 1 saat içinde yanıt gelmedi, otomatik onaylanıyor.")
    print("⏰ Telegram timeout — otomatik onaylandı.")
    return True, {}


def _wait_for_revise_message(offset, deadline) -> dict:
    """Kullanıcının revize talimatını bekler."""
    poll_interval = 5
    while time.time() < deadline:
        params = {"timeout": poll_interval, "allowed_updates": ["message"], "offset": offset}
        try:
            resp = requests.get(f"{BASE_URL}/getUpdates", params=params, timeout=poll_interval + 5)
            updates = resp.json().get("result", [])
        except:
            time.sleep(5)
            continue

        for update in updates:
            msg = update.get("message", {})
            text = msg.get("text", "").strip()
            if text:
                revize = {}
                text_lower = text.lower()
                if "caption:" in text_lower:
                    idx = text_lower.index("caption:") + len("caption:")
                    end = text_lower.index("görsel:") if "görsel:" in text_lower else len(text)
                    revize["caption"] = text[idx:end].strip()
                if "görsel:" in text_lower:
                    idx = text_lower.index("görsel:") + len("görsel:")
                    revize["image"] = text[idx:].strip()
                if not revize:
                    revize["caption"] = text  # varsayılan olarak caption

                _send_message(f"✏️ Revize talebi alındı:\n{text}\n\nYeniden hazırlanıyor...")
                print(f"✏️ Revize talimatı: {revize}")
                return revize

    return {}
