"""
Google Sheets entegrasyonu
- Feed listesini okur
- Geçmiş postları okur ve yazar
"""

import os
import json
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from config import GOOGLE_SHEET_ID

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly"
]

HISTORY_SHEET = "Geçmiş"
HISTORY_HEADERS = ["date", "topic", "source", "post_id", "caption"]

LOG_SHEET = "Log"
LOG_HEADERS = ["date", "status", "articles_found", "selected_topic", "source", "link", "notes"]


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
        print(f"📚 Geçmişte {len(records)} post bulundu.")
        return records
    except Exception as e:
        print(f"⚠️  Geçmiş okunamadı: {e}")
        return []


def save_log(status: str, articles: list[dict] = [], topic: dict = {}, notes: str = ""):
    """Her çalışmayı Log sayfasına yazar."""
    try:
        sh = get_spreadsheet()
        try:
            ws = sh.worksheet(LOG_SHEET)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=LOG_SHEET, rows=5000, cols=len(LOG_HEADERS))
            ws.append_row(LOG_HEADERS)

        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        if not articles and not topic:
            # Haber bulunamadı
            ws.append_row([now, status, 0, "", "", "", notes])
            print(f"📋 Log kaydedildi: {status}")
            return

        # Bulunan her haber için ayrı satır
        selected_title = topic.get("konu", "")
        selected_source = topic.get("source_name", "")

        for i, article in enumerate(articles):
            is_selected = article.get("title", "")[:30] in selected_title or article.get("source", "") == selected_source
            row_status = "✅ seçildi" if (is_selected and i == 0) else status
            ws.append_row([
                now if i == 0 else "",
                row_status if i == 0 else "",
                len(articles) if i == 0 else "",
                selected_title if i == 0 else "",
                article.get("source", ""),
                article.get("link", ""),
                article.get("title", "")
            ])

        print(f"📋 Log kaydedildi: {len(articles)} haber.")
    except Exception as e:
        print(f"⚠️  Log yazılamadı: {e}")


def save_to_history(topic: dict, post_id: str, caption: str):
    """Post edilen konuyu geçmiş sayfasına yazar."""
    try:
        sh = get_spreadsheet()
        try:
            ws = sh.worksheet(HISTORY_SHEET)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=HISTORY_SHEET, rows=1000, cols=len(HISTORY_HEADERS))
            ws.append_row(HISTORY_HEADERS)

        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            topic.get("konu", ""),
            topic.get("source_name", ""),
            post_id,
            caption[:200]
        ]
        ws.append_row(row)
        print(f"✓ Geçmişe kaydedildi.")
    except Exception as e:
        print(f"⚠️  Geçmişe yazılamadı: {e}")
