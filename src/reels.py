"""
Modül: Reels
Veo ile 9:16 dikey kısa video üretir.
"""

import time
from pathlib import Path
from google.genai import types
from config import VEO_MODEL
import gemini_client
import token_tracker

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

VIDEO_SECONDS = 8
VIDEO_COST_PER_SECOND = 0.03  # Veo 3.1 Lite, 720p sessiz
GENERATION_TIMEOUT = 600      # video üretimi bekleme üst sınırı (sn)


def build_video_prompt(topic: dict, revize_notu: str = "") -> str:
    subject = topic.get("gorsel_prompt", "abstract AI neural network visualization")
    style = (
        "Vertical 9:16 cinematic news reel background. Slow smooth camera movement, "
        "futuristic dark atmosphere, deep blue and black tones, neon cyan and purple "
        "accent lights, subtle particle effects, NO text, NO watermark"
    )
    prompt = f"{subject}. {style}"
    if revize_notu:
        prompt += f". Revision request: {revize_notu}"
    return prompt


def generate_reel_video(topic: dict, revize_notu: str = "") -> Path:
    """Veo ile 8 saniyelik dikey video üretir, mp4 yolunu döner."""
    client = gemini_client.get_client()
    prompt = build_video_prompt(topic, revize_notu)

    print(f"🎬 Reel videosu üretiliyor (Veo, 1-3 dk sürebilir)...")

    operation = client.models.generate_videos(
        model=VEO_MODEL,
        prompt=prompt,
        config=types.GenerateVideosConfig(
            number_of_videos=1,
            aspect_ratio="9:16",
            duration_seconds=VIDEO_SECONDS,
        ),
    )

    deadline = time.time() + GENERATION_TIMEOUT
    while not operation.done:
        if time.time() > deadline:
            raise TimeoutError("Veo video üretimi zaman aşımına uğradı.")
        time.sleep(15)
        operation = client.operations.get(operation)

    result = getattr(operation, "response", None) or getattr(operation, "result", None)
    videos = getattr(result, "generated_videos", None)
    if not videos:
        raise ValueError(f"Veo video üretemedi: {getattr(operation, 'error', operation)}")

    video = videos[0].video
    path = OUTPUT_DIR / "reel.mp4"
    client.files.download(file=video)
    video.save(str(path))

    token_tracker.add_cost(VIDEO_SECONDS * VIDEO_COST_PER_SECOND)
    print(f"✓ Reel videosu hazır: {path}")
    return path
