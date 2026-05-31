"""
Modül 4: Instagram Yayını
Upload-post.com API ile görsel + caption post atar.
"""

import os
import requests
import time
from pathlib import Path

UPLOAD_POST_API_KEY = os.getenv("UPLOAD_POST_API_KEY")
UPLOAD_POST_USER    = os.getenv("UPLOAD_POST_USER")
API_URL    = "https://api.upload-post.com/api/upload_photos"
STATUS_URL = "https://api.upload-post.com/api/uploadposts/status"


def post_to_instagram(image_path: Path, caption: str) -> str:
    print("\n📤 Upload-post.com üzerinden Instagram'a gönderiliyor...")

    if not UPLOAD_POST_API_KEY or not UPLOAD_POST_USER:
        raise ValueError("UPLOAD_POST_API_KEY veya UPLOAD_POST_USER eksik.")

    print(f"  Görsel yolu: {image_path} | Mevcut: {Path(image_path).exists()}")
    with open(image_path, "rb") as f:
        response = requests.post(
            API_URL,
            headers={"Authorization": f"Apikey {UPLOAD_POST_API_KEY}"},
            data={
                "title": caption[:100],
                "description": caption,
                "user": UPLOAD_POST_USER,
                "platform[]": "instagram",
                "async_upload": "true",
            },
            files={"photos[]": (image_path.name, f, "image/png")}
        )

    data = response.json()

    if not response.ok:
        raise ValueError(f"Upload-post hatası: {data}")

    request_id = data.get("request_id", "")
    print(f"✓ Yükleme başlatıldı. Request ID: {request_id}")

    _wait_for_completion(request_id)
    return request_id


def _wait_for_completion(request_id: str, timeout: int = 120):
    print("  Yükleme durumu kontrol ediliyor...")

    for _ in range(timeout // 10):
        time.sleep(10)

        response = requests.get(
            STATUS_URL,
            headers={"Authorization": f"Apikey {UPLOAD_POST_API_KEY}"},
            params={"request_id": request_id}
        )
        data = response.json()
        status = data.get("status", "")

        if status == "completed":
            results = data.get("results", [])
            for r in results:
                if r.get("platform") == "instagram":
                    url = r.get("post_url", "")
                    print(f"✓ Instagram'da yayınlandı! {url}")
            return

        elif status == "failed":
            raise ValueError(f"Yükleme başarısız: {data}")

        else:
            print(f"  Bekleniyor... ({status})")

    raise TimeoutError("Yükleme zaman aşımına uğradı.")
