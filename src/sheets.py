"""
Google Sheets entegrasyonu
- Feed listesini okur
- Geçmiş postları okur ve yazar
"""

import os
import json
from datetime import datetime, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials
from config import GOOGLE_SHEET_ID

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly"
]

HISTORY_SHEET = "Geçmiş"
HISTORY_HEADERS = ["date", "topic", "post_type", "post_id", "source", "source_link", "caption"]

LOG_SHEET = "Log"
LOG_HEADERS = ["date", "status", "post_type", "telegram", "articles_found", "selected_topic", "score", "source", "link", "title", "input_tokens", "output_tokens", "cost_usd", "api_errors", "notes"]


def get_client():
    """Google Sheets istemcisi oluşturur."""
    service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT")
    if not service_account_json:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT ortam değişkeni eksik.")
    info = json.loads(service_account_json)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)


def get_spreadsheet():
    client = get_client()
    return client.open_by_key(GOOGLE_SHEET_ID)


SETTINGS_SHEET = "Ayarlar"


def _get_settings_sheet():
    """Ayarlar sayfasını döner, yoksa oluşturur."""
    sh = get_spreadsheet()
    try:
        return sh.worksheet(SETTINGS_SHEET)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=SETTINGS_SHEET, rows=50, cols=3)
        ws.append_rows([
            ["key", "value", "açıklama"],
            ["bot_status", "active", "active veya paused — pause tüm botu (reels dahil) durdurur"],
            ["reels_status", "pause", "manuel / otomatik / pause — Telegram: 'reels manuel' vb. ile değiştirilebilir"],
            ["story_status", "otomatik", "otomatik / pause — reel yayınlanınca story olarak da paylaşılır"],
        ])
        print("✓ Ayarlar sayfası oluşturuldu.")
        return ws


def get_setting(key: str, default: str = "") -> str:
    """Ayarlar sayfasından bir değer okur."""
    try:
        ws = _get_settings_sheet()
        for row in ws.get_all_values()[1:]:
            if len(row) >= 2 and row[0].strip().lower() == key.lower():
                return row[1].strip()
    except Exception as e:
        print(f"⚠️  Ayar okunamadı ({key}): {e}")
    return default


def set_setting(key: str, value: str):
    """Ayarlar sayfasındaki bir değeri günceller, yoksa ekler."""
    try:
        ws = _get_settings_sheet()
        rows = ws.get_all_values()
        for i, row in enumerate(rows):
            if len(row) >= 1 and row[0].strip().lower() == key.lower():
                ws.update_cell(i + 1, 2, value)
                print(f"✓ Ayar güncellendi: {key} → {value}")
                return
        ws.append_row([key, value, ""])
        print(f"✓ Ayar eklendi: {key} → {value}")
    except Exception as e:
        print(f"⚠️  Ayar yazılamadı ({key}): {e}")


def get_bot_status() -> str:
    return get_setting("bot_status", "active")


def set_bot_status(status: str):
    set_setting("bot_status", status)


def load_history() -> list[dict]:
    """Geçmiş sayfasındaki post edilmiş konuları döndürür."""
    try:
        sh = get_spreadsheet()
        try:
            ws = sh.worksheet(HISTORY_SHEET)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=HISTORY_SHEET, rows=1000, cols=len(HISTORY_HEADERS))
            ws.append_row(HISTORY_HEADERS)
            return []

        records = ws.get_all_records()

        # Son 15 günü filtrele
        cutoff = datetime.now(timezone(timedelta(hours=3))) - timedelta(days=15)
        recent = []
        for r in records:
            try:
                date = datetime.strptime(r.get("date", "")[:16], "%Y-%m-%d %H:%M")
                if date >= cutoff:
                    recent.append(r)
            except:
                pass

        print(f"📚 Geçmişte {len(recent)} post bulundu (son 15 gün).")
        return recent
    except Exception as e:
        print(f"⚠️  Geçmiş okunamadı: {e}")
        return []


def save_log(status: str, articles: list[dict] = [], topic: dict = {},
             notes: str = "", post_type: str = "", telegram: str = "",
             tokens: dict = {}):
    """Her çalışmayı Log sayfasına yazar."""
    try:
        sh = get_spreadsheet()
        try:
            ws = sh.worksheet(LOG_SHEET)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=LOG_SHEET, rows=5000, cols=len(LOG_HEADERS))
            ws.append_row(LOG_HEADERS)

        now = datetime.now(timezone(timedelta(hours=3))).strftime("%Y-%m-%d %H:%M")

        input_t  = tokens.get("input_tokens", "")
        output_t = tokens.get("output_tokens", "")
        cost     = tokens.get("cost_usd", "")
        api_err  = tokens.get("api_errors", "")

        if not articles and not topic:
            ws.append_row([now, status, post_type, telegram, 0, "", "", "", "", "", input_t, output_t, cost, api_err, notes])
            print(f"📋 Log kaydedildi: {status}")
            return

        selected_title = topic.get("konu", "")
        selected_score = topic.get("score", "")

        rows = []
        for i, article in enumerate(articles):
            rows.append([
                now if i == 0 else "",
                status if i == 0 else "",
                post_type if i == 0 else "",
                telegram if i == 0 else "",
                len(articles) if i == 0 else "",
                selected_title if i == 0 else "",
                selected_score if i == 0 else "",
                article.get("source", ""),
                article.get("link", ""),
                article.get("title", ""),
                input_t if i == 0 else "",
                output_t if i == 0 else "",
                cost if i == 0 else "",
                api_err if i == 0 else "",
                notes if i == 0 else ""
            ])

        # Tüm satırlar tek API çağrısında yazılır (kota dostu)
        ws.append_rows(rows, value_input_option="RAW")
        print(f"📋 Log kaydedildi: {len(articles)} haber.")
    except Exception as e:
        print(f"⚠️  Log yazılamadı: {e}")


def save_to_history(topic: dict, post_id: str, caption: str, post_type: str = "tek post", articles: list[dict] = []):
    """Post edilen konuyu geçmiş sayfasına yazar. Birden fazla kaynak varsa ayrı satır."""
    try:
        sh = get_spreadsheet()
        try:
            ws = sh.worksheet(HISTORY_SHEET)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=HISTORY_SHEET, rows=1000, cols=len(HISTORY_HEADERS))
            ws.append_row(HISTORY_HEADERS)

        now = datetime.now(timezone(timedelta(hours=3))).strftime("%Y-%m-%d %H:%M")
        konu = topic.get("konu", "")

        if articles:
            rows = []
            for i, article in enumerate(articles):
                rows.append([
                    now if i == 0 else "",
                    konu if i == 0 else "",
                    post_type if i == 0 else "",
                    post_id if i == 0 else "",
                    article.get("source", ""),
                    article.get("link", ""),
                    caption[:200] if i == 0 else ""
                ])
            ws.append_rows(rows, value_input_option="RAW")
        else:
            ws.append_row([
                now, konu, post_type, post_id,
                topic.get("source_name", ""),
                topic.get("source_link", ""),
                caption[:200]
            ])

        print(f"✓ Geçmişe kaydedildi.")
    except Exception as e:
        print(f"⚠️  Geçmişe yazılamadı: {e}")
