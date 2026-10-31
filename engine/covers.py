"""Grab one frame from the kept source. Full typography stays in sayframe's cover stack."""

from __future__ import annotations

from pathlib import Path

from engine.errors import TalkCutError
from engine.media import run


def grab(ffmpeg: str, video: Path, at: float, dest: Path) -> Path:
    if at < 0:
        raise TalkCutError("封面时间无效。")
    dest.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            ffmpeg,
            "-y",
            "-v",
            "error",
            "-ss",
            f"{at:.3f}",
            "-i",
            str(video),
            "-frames:v",
            "1",
            str(dest),
        ]
    )
    if not dest.is_file():
        raise TalkCutError("没有抽出封面帧。")
    return dest
