import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv(AQ.Ab8RN6L4WvlhmmCiEmSRox_EUGx2D_k6XaPDxiOggk-I6Y--rA)
UPLOAD_POST_API_KEY = os.getenv(eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6ImVjZW96a3VsQGdtYWlsLmNvbSIsImV4cCI6NDkzMzc3MTI4NiwianRpIjoiZGUxYTQ4YWMtYjQ5MS00OTExLWJkYzItZmM0OTBhZmRmODc5In0.yufVrutv4cvDlqL7dr6efZJ6gpQfPcJmEGkXgvNfagw)
UPLOAD_POST_USER = os.getenv(eceozkul@gmail.com)

LANGUAGE = os.getenv("LANGUAGE", "tr")

GEMINI_TEXT_MODEL = "gemini-2.0-flash"
GEMINI_IMAGE_MODEL = "gemini-2.0-flash-preview-image-generation"

RSS_FEEDS = [
    {"name": "Anthropic Blog",  "url": "https://www.anthropic.com/rss.xml",                                 "priority": 1},
    {"name": "TechCrunch AI",   "url": "https://techcrunch.com/category/artificial-intelligence/feed/",     "priority": 2},
    {"name": "The Verge AI",    "url": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml", "priority": 2},
    {"name": "ArXiv CS.AI",     "url": "https://rss.arxiv.org/rss/cs.AI",                                   "priority": 3},
]

IMAGE_SIZE = 1080

HASHTAGS = [
    "#yapayzekahaberleri", "#teknoloji", "#AI", "#YapayZeka",
    "#makineöğrenmesi", "#gelecek", "#inovasyon",
    "#dijitaldönüşüm", "#deeplearning", "#AIhaberleri"
]
