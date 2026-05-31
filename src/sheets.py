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
