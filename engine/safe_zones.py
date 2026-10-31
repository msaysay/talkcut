"""Face boxes as caption keep-out zones.

MediaPipe Face Detector (Apache-2.0) is sampled every 0.5s. Each box is
expanded before captions or cards are allowed to overlap it.
"""

from __future__ import annotations

import os

os.environ.setdefault("GLOG_minloglevel", "2")

import json
import subprocess
from pathlib import Path

from engine.errors import TalkCutError

EXPAND = 0.18
SAMPLE_SECONDS = 0.5
MODEL_NAME = "blaze_face_short_range.tflite"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_detector/"
    "blaze_face_short_range/float16/1/blaze_face_short_range.tflite"
)


def expand_box(box: dict, ratio: float = EXPAND) -> dict:
    """Grow a normalized box around its center and clamp it to the frame."""
    width = min(1.0, box["w"] * (1 + ratio))
    height = min(1.0, box["h"] * (1 + ratio))
    cx = box["x"] + box["w"] / 2
    cy = box["y"] + box["h"] / 2
    x = min(max(0.0, cx - width / 2), 1 - width)
    y = min(max(0.0, cy - height / 2), 1 - height)
    return {"x": round(x, 4), "y": round(y, 4), "w": round(width, 4), "h": round(height, 4)}


def overlap_area(a: dict, b: dict) -> float:
    ix = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
    iy = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
    if ix <= 0 or iy <= 0:
        return 0.0
    return ix * iy


def choose_anchor(face: dict | None) -> str:
    """Put the caption in the band that overlaps the expanded face less."""
    if not face:
        return "bottom"
    lower = {"x": 0.04, "y": 0.66, "w": 0.92, "h": 0.28}
    upper = {"x": 0.04, "y": 0.04, "w": 0.92, "h": 0.24}
    if overlap_area(face, lower) > overlap_area(face, upper):
        return "top"
    return "bottom"


def face_at(samples: list[dict], time: float) -> dict | None:
    if not samples:
        return None
    nearest = min(samples, key=lambda row: abs(row["time"] - time))
    faces = nearest.get("faces") or []
    return faces[0] if faces else None


def detect_safe_zones(video: Path, duration: float, model_path: Path, ffmpeg: str) -> dict:
    try:
        import mediapipe as mp
        from mediapipe.tasks.python import BaseOptions, vision
        from PIL import Image
        import numpy as np
    except ImportError as exc:
        raise TalkCutError("需要 mediapipe 和 pillow 才能做人脸安全区。pip install mediapipe pillow") from exc
    if not model_path.is_file():
        raise TalkCutError(f"缺少人脸模型 {model_path}。运行 setup --vision 下载（Apache-2.0）。")
    options = vision.FaceDetectorOptions(base_options=BaseOptions(model_asset_path=str(model_path)))
    detector = vision.FaceDetector.create_from_options(options)
    samples = []
    time = 0.0
    while time < duration - 0.05:
        frame = _grab_frame(ffmpeg, video, time)
        image = Image.open(frame).convert("RGB")
        array = np.asarray(image)
        width, height = image.size
        detected = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=array))
        faces = []
        for detection in detected.detections:
            box = detection.bounding_box
            normalized = {
                "x": box.origin_x / width,
                "y": box.origin_y / height,
                "w": box.width / width,
                "h": box.height / height,
            }
            faces.append(expand_box(normalized))
        samples.append({"time": round(time, 2), "faces": faces})
        time += SAMPLE_SECONDS
        frame.unlink(missing_ok=True)
    return {
        "version": 1,
        "interval": SAMPLE_SECONDS,
        "expand": EXPAND,
        "model": MODEL_NAME,
        "license": "Apache-2.0",
        "samples": samples,
    }


def write_safe_zones(payload: dict, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _grab_frame(ffmpeg: str, video: Path, time: float) -> Path:
    dest = video.with_name(f".face-{time:.2f}.png")
    subprocess.run(
        [ffmpeg, "-y", "-v", "error", "-ss", f"{time:.3f}", "-i", str(video), "-frames:v", "1", str(dest)],
        check=True,
        capture_output=True,
    )
    return dest
