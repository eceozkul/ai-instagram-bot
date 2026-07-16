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


def _handle_command(text: str) -> bool:
    """
    Bilinen bir Telegram komutunu işler. İşlediyse True döner.
    Hem çalışma başındaki kontrolde hem onay beklerken gelen mesajlarda kullanılır.
    """
    from sheets import set_bot_status, get_bot_status, get_setting, set_setting, save_log

    text = text.strip().lower()

    if text == "/pause":
        set_bot_status("paused")
        _send_message("⏸️ Bot duraklatıldı. Devam ettirmek için /resume yaz.")
        print("⏸️ Bot pause edildi.")
        save_log("⏸️ pause", notes="Telegram'dan /pause komutu alındı.")
        return True

    if text == "/resume":
        set_bot_status("active")
        _send_message("▶️ Bot yeniden aktif!")
        print("▶️ Bot resume edildi.")
        save_log("▶️ resume", notes="Telegram'dan /resume komutu alındı.")
        return True

    if text == "/status":
        status = get_bot_status()
        reels = get_setting("reels_status", "pause")
        _send_message(
            f"Bot durumu: {'▶️ Aktif' if status == 'active' else '⏸️ Duraklatılmış'}\n"
            f"Reels modu: {reels}"
        )
        return True

    # Reels modunu değiştir: "reels manuel" / "reels otomatik" / "reels pause"
    for mode in ("manuel", "otomatik", "pause"):
        if text in (f"reels {mode}", f"/reels {mode}"):
            set_setting("reels_status", mode)
            _send_message(f"🎬 Reels modu güncellendi: {mode}")
            print(f"🎬 Reels modu → {mode}")
            save_log("🎬 reels modu", notes=f"Telegram'dan reels modu {mode} yapıldı.")
            return True

    if text in ("/reels", "reels"):
        reels_status = get_setting("reels_status", "pause").lower()
        if reels_status.startswith("manu"):
            set_setting("reels_request", "pending")
            _send_message("🎬 Reel talebi alındı — bir sonraki çalışmada günün en önemli haberinden reel üretilecek.")
            print("🎬 Manuel reel talebi kaydedildi.")
            save_log("🎬 reel talebi", notes="Telegram'dan reels komutu alındı.")
        elif reels_status == "otomatik":
            _send_message("ℹ️ Reels otomatik modda — her gün en önemli haberden zaten reel üretiliyor.")
        else:
            _send_message(
                "⏸️ Reels şu an pause modunda.\n"
                "Değiştirmek için yaz: <b>reels manuel</b> / <b>reels otomatik</b> / <b>reels pause</b>"
            )
        return True

    return False


def check_commands():
    """Telegram'dan bekleyen komutları okur ve işler."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    try:
        resp = requests.get(f"{BASE_URL}/getUpdates", params={"allowed_updates": ["message"]}, timeout=10)
        updates = resp.json().get("result", [])

        if not updates:
            return

        last_offset = None
        for update in updates:
            last_offset = update["update_id"] + 1
            msg = update.get("message", {})
            text = msg.get("text", "")
            if text:
                _handle_command(text)

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


def notify(text: str):
    """Bilgi mesajı gönderir (onay istemez). Asla exception fırlatmaz."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        requests.post(f"{BASE_URL}/sendMessage", json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text[:4000],
        }, timeout=10)
    except Exception:
        pass


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


def send_reel_for_approval(video_path: Path, caption: str, topic: dict) -> tuple[bool, dict]:
    """Reel videosunu onay için Telegram'a gönderir."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️  Telegram ayarları eksik, otomatik onaylanıyor.")
        return True, {}

    info_text = (
        f"🎬 REEL | Puan: {topic.get('score', '?')}/10\n\n"
        f"📰 {topic.get('konu', '')}\n"
        f"📌 Kaynak: {topic.get('source_name', '')}\n\n"
        f"Caption:\n{caption[:400]}"
    )
    _send_message(info_text)

    message_id = _send_video_with_buttons(video_path)
    if not message_id:
        print("⚠️  Telegram videosu gönderilemedi, otomatik onaylanıyor.")
        return True, {}

    print(f"📱 Reel Telegram'a gönderildi. Onay bekleniyor (max 1 saat)...")
    return _wait_for_callback(message_id, timeout=3600)


def _send_video_with_buttons(video_path: Path) -> int | None:
    """Videoyu inline butonlarla gönderir, message_id döner."""
    import json
    keyboard = json.dumps({
        "inline_keyboard": [[
            {"text": "✅ Onayla",     "callback_data": "approve"},
            {"text": "✏️ Revize Et", "callback_data": "revise"},
            {"text": "❌ Atla",       "callback_data": "skip"}
        ]]
    })
    with open(video_path, "rb") as f:
        response = requests.post(
            f"{BASE_URL}/sendVideo",
            data={
                "chat_id": TELEGRAM_CHAT_ID,
                "reply_markup": keyboard
            },
            files={"video": f},
            timeout=120
        )

    if response.ok:
        return response.json()["result"]["message_id"]
    print(f"⚠️  Telegram video gönderilemedi: {response.text}")
    return None


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


def _confirm_offset(offset):
    """İşlenen update'leri Telegram tarafında okundu olarak işaretler."""
    if offset:
        try:
            requests.get(f"{BASE_URL}/getUpdates", params={"offset": offset, "timeout": 0}, timeout=10)
        except Exception:
            pass


def _wait_for_callback(message_id: int, timeout: int = 1800) -> tuple[bool, dict]:
    """
    Telegram callback'i polling ile bekler.
    Sadece bu onaya ait mesajın (message_id) butonları kabul edilir —
    önceki onaylardan kalan bayat callback'ler yok sayılır.
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
            if not cb:
                # Onay beklerken yazılan komutlar kaybolmasın (/pause, reels vb.)
                text = update.get("message", {}).get("text", "")
                if text:
                    _handle_command(text)
                continue

            requests.post(f"{BASE_URL}/answerCallbackQuery", json={"callback_query_id": cb["id"]})

            # Başka bir onay mesajına ait (bayat) callback — yok say
            cb_message_id = cb.get("message", {}).get("message_id")
            if cb_message_id != message_id:
                print(f"  ⏭️  Bayat callback yok sayıldı (mesaj {cb_message_id}, beklenen {message_id}).")
                continue

            data = cb.get("data")

            if data == "approve":
                _confirm_offset(offset)
                _send_message("✅ Onaylandı! Gönderiliyor...")
                print("✅ Telegram onayı alındı.")
                return True, {}

            elif data == "skip":
                _confirm_offset(offset)
                _send_message("❌ Atlandı.")
                print("❌ Telegram'dan atla komutu geldi.")
                return False, {}

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
