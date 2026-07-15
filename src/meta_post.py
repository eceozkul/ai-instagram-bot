"""
Meta Graph API — Instagram Direct Publishing
Görselleri repoya commit eder, Meta'ya raw URL verir.
"""

import os
import time
import subprocess
import requests
from datetime import datetime, timedelta
from pathlib import Path

META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
IG_BUSINESS_ID    = os.getenv("IG_BUSINESS_ID")
GITHUB_REPO       = os.getenv("GITHUB_REPO", "eceozkul/ai-instagram-bot")

GRAPH_URL = "https://graph.instagram.com/v21.0"
OUTPUT_DIR = Path("output")

RETRIES = 3
BASE_DELAY = 5


def _request(method: str, url: str, **kwargs) -> requests.Response:
    """Meta API isteği — ağ hataları ve 5xx yanıtlarında tekrar dener."""
    kwargs.setdefault("timeout", 60)
    last_err = None
    for attempt in range(1, RETRIES + 1):
        try:
            r = requests.request(method, url, **kwargs)
            if r.status_code >= 500:
                raise requests.RequestException(f"HTTP {r.status_code}: {r.text[:200]}")
            return r
        except requests.RequestException as e:
            last_err = e
            if attempt < RETRIES:
                wait = BASE_DELAY * attempt
                print(f"  ⚠️  Meta isteği hatası (deneme {attempt}/{RETRIES}), {wait} sn sonra tekrar: {e}")
                time.sleep(wait)
    raise last_err


def _commit_and_push(paths: list[Path], message: str) -> list[str]:
    """Görselleri repoya commit eder, raw URL listesini döner."""
    subprocess.run(["git", "config", "user.email", "bot@github.actions"], check=True)
    subprocess.run(["git", "config", "user.name", "AI Bot"], check=True)

    for path in paths:
        subprocess.run(["git", "add", str(path)], check=True)

    subprocess.run(["git", "commit", "-m", message], check=True)
    subprocess.run(["git", "push"], check=True)

    # Commit sonrası raw URL'leri al — yol repo köküne göre olmalı
    repo_root = Path(subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True
    ).stdout.strip())

    urls = []
    for path in paths:
        rel = path.resolve().relative_to(repo_root)
        url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{rel}"
        urls.append(url)

    # URL'lerin gerçekten erişilebilir olmasını bekle
    for url in urls:
        for attempt in range(20):
            try:
                r = requests.head(url, timeout=10, allow_redirects=True)
                if r.status_code == 200 and "image" in r.headers.get("Content-Type", ""):
                    print(f"  ✓ URL hazır: {url}")
                    break
            except Exception:
                pass
            time.sleep(5)
        else:
            print(f"  ⚠️  URL erişilemez kaldı: {url}")
    return urls


def _clean_old_images(days: int = 3):
    """N günden eski görselleri siler ve commit eder."""
    if not OUTPUT_DIR.exists():
        return

    cutoff = time.time() - (days * 86400)
    deleted = []
    for path in OUTPUT_DIR.glob("*.png"):
        if path.stat().st_mtime < cutoff:
            path.unlink()
            deleted.append(str(path))

    if deleted:
        subprocess.run(["git", "config", "user.email", "bot@github.actions"], check=True)
        subprocess.run(["git", "config", "user.name", "AI Bot"], check=True)
        for f in deleted:
            subprocess.run(["git", "rm", f], check=False)
        subprocess.run(["git", "commit", "-m", f"Clean up {len(deleted)} old images"], check=False)
        subprocess.run(["git", "push"], check=False)
        print(f"🗑️  {len(deleted)} eski görsel silindi.")


def post_to_instagram(image_path: Path, caption: str) -> str:
    """Meta Graph API ile Instagram'a tek görsel post atar."""
    print("\n📤 Meta Graph API üzerinden Instagram'a gönderiliyor...")

    if not META_ACCESS_TOKEN or not IG_BUSINESS_ID:
        raise ValueError("META_ACCESS_TOKEN veya IG_BUSINESS_ID eksik.")

    # 1. Görseli commit et, URL al
    urls = _commit_and_push([image_path], f"Post image: {image_path.name}")
    image_url = urls[0]
    print(f"  Görsel URL: {image_url}")

    # 2. Media container oluştur
    r = _request("post", f"{GRAPH_URL}/me/media", data={
        "image_url":    image_url,
        "caption":      caption,
        "access_token": META_ACCESS_TOKEN,
    })
    data = r.json()
    if "id" not in data:
        raise ValueError(f"Media container hatası: {data}")
    creation_id = data["id"]
    print(f"  Container ID: {creation_id}")

    # 3. Container'ın hazır olmasını bekle
    _wait_for_container(creation_id)

    # 4. Publish
    r = _request("post", f"{GRAPH_URL}/me/media_publish", data={
        "creation_id":  creation_id,
        "access_token": META_ACCESS_TOKEN,
    })
    data = r.json()
    if "id" not in data:
        raise ValueError(f"Publish hatası: {data}")

    post_id = data["id"]
    print(f"✓ Instagram'da yayınlandı! Post ID: {post_id}")

    _clean_old_images()
    return post_id


def post_carousel_to_instagram(image_paths: list[Path], caption: str) -> str:
    """Meta Graph API ile carousel post atar."""
    print(f"\n📤 Meta Graph API üzerinden carousel gönderiliyor ({len(image_paths)} slayt)...")

    if not META_ACCESS_TOKEN or not IG_BUSINESS_ID:
        raise ValueError("META_ACCESS_TOKEN veya IG_BUSINESS_ID eksik.")

    # 1. Tüm görselleri commit et
    urls = _commit_and_push(image_paths, f"Carousel: {len(image_paths)} images")

    # 2. Her görsel için container oluştur (is_carousel_item=true)
    child_ids = []
    for url in urls:
        r = _request("post", f"{GRAPH_URL}/me/media", data={
            "image_url":         url,
            "is_carousel_item":  "true",
            "access_token":      META_ACCESS_TOKEN,
        })
        data = r.json()
        if "id" not in data:
            raise ValueError(f"Carousel child container hatası: {data}")
        child_ids.append(data["id"])
        print(f"  Child container: {data['id']}")

    # Container'ların hazır olmasını bekle
    for cid in child_ids:
        _wait_for_container(cid)

    # 3. Carousel container oluştur
    r = _request("post", f"{GRAPH_URL}/me/media", data={
        "media_type":   "CAROUSEL",
        "children":     ",".join(child_ids),
        "caption":      caption,
        "access_token": META_ACCESS_TOKEN,
    })
    data = r.json()
    if "id" not in data:
        raise ValueError(f"Carousel container hatası: {data}")
    creation_id = data["id"]
    _wait_for_container(creation_id)

    # 4. Publish
    r = _request("post", f"{GRAPH_URL}/me/media_publish", data={
        "creation_id":  creation_id,
        "access_token": META_ACCESS_TOKEN,
    })
    data = r.json()
    if "id" not in data:
        raise ValueError(f"Carousel publish hatası: {data}")

    post_id = data["id"]
    print(f"✓ Carousel Instagram'da yayınlandı! Post ID: {post_id}")

    _clean_old_images()
    return post_id


def _wait_for_container(creation_id: str, timeout: int = 60):
    """Container'ın FINISHED durumuna gelmesini bekler."""
    for _ in range(timeout // 3):
        r = _request("get", f"{GRAPH_URL}/{creation_id}", params={
            "fields":       "status_code",
            "access_token": META_ACCESS_TOKEN,
        })
        status = r.json().get("status_code")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise ValueError(f"Container hazırlanamadı: {r.json()}")
        time.sleep(3)
    raise TimeoutError(f"Container timeout: {creation_id}")
