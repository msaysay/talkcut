"""Person matte for the behind-the-subject layout.

Uses MediaPipe's selfie segmenter (Apache-2.0). This is not Robust Video
Matting. The output is a short VP9 WebM with alpha for Remotion to stack
over the type.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

os.environ.setdefault("GLOG_minloglevel", "2")

from engine.errors import TalkCutError

SEGMENTER_NAME = "selfie_segmenter.tflite"
SEGMENTER_URL = (
    "https://storage.googleapis.com/mediapipe-models/image_segmenter/"
    "selfie_segmenter/float16/latest/selfie_segmenter.tflite"
)


def build_person_webm(
    ffmpeg: str,
    video: Path,
    start: float,
    end: float,
    model_path: Path,
    dest: Path,
    fps: int = 8,
    label: str = "",
    font_path: Path | None = None,
) -> Path:
    try:
        import mediapipe as mp
        import numpy as np
        from mediapipe.tasks.python import BaseOptions, vision
        from PIL import Image
    except ImportError as exc:
        raise TalkCutError("抠像需要 mediapipe 和 pillow。") from exc
    if not model_path.is_file():
        raise TalkCutError(f"缺少分割模型 {model_path}。运行 setup --vision。")
    if end - start < 0.2:
        raise TalkCutError("抠像片段太短。")
    work = dest.with_suffix(".frames")
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    options = vision.ImageSegmenterOptions(
        base_options=BaseOptions(model_asset_path=str(model_path)),
        output_confidence_masks=True,
    )
    segmenter = vision.ImageSegmenter.create_from_options(options)
    count = max(1, int(round((end - start) * fps)))
    for index in range(count):
        at = start + index / fps
        raw = work / f"raw_{index:04d}.png"
        subprocess.run(
            [ffmpeg, "-y", "-v", "error", "-ss", f"{at:.3f}", "-i", str(video), "-frames:v", "1", str(raw)],
            check=True,
            capture_output=True,
        )
        image = Image.open(raw).convert("RGB")
        array = np.asarray(image)
        result = segmenter.segment(mp.Image(image_format=mp.ImageFormat.SRGB, data=array))
        mask = np.asarray(result.confidence_masks[0].numpy_view())
        if mask.shape[:2] != array.shape[:2]:
            mask = np.transpose(mask) if mask.shape[:2] == array.shape[:2][::-1] else mask
        if mask.shape[:2] != array.shape[:2]:
            mask_image = Image.fromarray((np.clip(mask, 0, 1) * 255).astype(np.uint8)).resize(image.size)
            alpha = np.asarray(mask_image)
        else:
            alpha = (np.clip(mask, 0, 1) * 255).astype(np.uint8)
        plate = Image.new("RGB", image.size, (26, 18, 12))
        if label and font_path and font_path.is_file():
            from PIL import ImageDraw, ImageFont

            draw = ImageDraw.Draw(plate)
            face = ImageFont.truetype(str(font_path), max(48, image.size[0] // 8))
            wrapped = _wrap(label, 8)
            draw.multiline_text((image.size[0] * 0.08, image.size[1] * 0.36), wrapped, font=face, fill=(255, 246, 216), spacing=16)
        person = image.convert("RGBA")
        person.putalpha(Image.fromarray(alpha))
        plate.paste(person, mask=person.getchannel("A"))
        plate.save(work / f"rgba_{index:04d}.png")
        raw.unlink(missing_ok=True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-v",
            "error",
            "-framerate",
            str(fps),
            "-i",
            str(work / "rgba_%04d.png"),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(dest),
        ],
        check=True,
        capture_output=True,
    )
    shutil.rmtree(work, ignore_errors=True)
    return dest


def _wrap(text: str, per_line: int) -> str:
    return "\n".join(text[index : index + per_line] for index in range(0, len(text), per_line))
