import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
UPLOAD_POST_API_KEY = os.getenv("UPLOAD_POST_API_KEY")
UPLOAD_POST_USER = os.getenv("UPLOAD_POST_USER")

LANGUAGE = os.getenv("LANGUAGE", "tr")

GEMINI_TEXT_MODEL = "gemini-1.5-flash"
GEMINI_IMAGE_MODEL = "gemini-1.5-flash"

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
