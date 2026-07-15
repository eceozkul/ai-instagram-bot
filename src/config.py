import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

LANGUAGE = os.getenv("LANGUAGE", "tr")

GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "1_pUUpZLwqsDSIQhIVNdrZhgzX3f3gUxPdSdL00sNjyw")

GEMINI_TEXT_MODEL = "gemini-2.5-flash"
GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"
VEO_MODEL = "veo-3.1-lite-generate-preview"  # 720p sessiz, ~$0.03/sn; kalite için: veo-3.1-fast

# Google Sheet okunamazsa kullanılacak yedek liste — sadece çalıştığı doğrulanmış feed'ler
RSS_FEEDS = [
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "priority": 1},
    {"name": "Hacker News",   "url": "https://news.ycombinator.com/rss",                              "priority": 1},
    {"name": "VentureBeat AI","url": "https://venturebeat.com/category/ai/feed/",                     "priority": 2},
]

IMAGE_SIZE = 1080

HASHTAGS = [
    "#yapayzekahaberleri", "#teknoloji", "#AI", "#YapayZeka",
    "#makineöğrenmesi", "#gelecek", "#inovasyon",
    "#dijitaldönüşüm", "#deeplearning", "#AIhaberleri"
]
