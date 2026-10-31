"""ffmpeg helpers. Paths come from runtime discovery, never a fixed host install."""

from __future__ import annotations

import array
import hashlib
import json
import subprocess
from pathlib import Path

from engine.errors import TalkCutError


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(cmd: list[str], *, timeout: int = 120) -> subprocess.CompletedProcess[bytes]:
    try:
        completed = subprocess.run(cmd, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise TalkCutError(f"命令超时：{cmd[0]}") from exc
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", "replace").strip()
        raise TalkCutError(detail or f"命令失败：{cmd[0]}")
    return completed


def probe(ffprobe: str, path: Path) -> dict:
    completed = run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-show_entries",
            "stream=codec_type,width,height",
            "-of",
            "json",
            str(path),
        ]
    )
    payload = json.loads(completed.stdout.decode("utf-8"))
    duration = float(payload.get("format", {}).get("duration") or 0)
    streams = payload.get("streams") or []
    has_video = any(item.get("codec_type") == "video" for item in streams)
    has_audio = any(item.get("codec_type") == "audio" for item in streams)
    video = next((item for item in streams if item.get("codec_type") == "video"), {})
    if duration <= 0:
        raise TalkCutError("无法读取媒体时长。")
    return {
        "duration": duration,
        "hasVideo": has_video,
        "hasAudio": has_audio,
        "width": int(video.get("width") or 0),
        "height": int(video.get("height") or 0),
    }


def load_pcm(ffmpeg: str, path: Path, sample_rate: int = 16000) -> array.array:
    completed = run(
        [
            ffmpeg,
            "-v",
            "error",
            "-i",
            str(path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-f",
            "s16le",
            "-",
        ],
        timeout=180,
    )
    samples = array.array("h")
    raw = completed.stdout
    if len(raw) % 2:
        raw = raw[:-1]
    samples.frombytes(raw)
    if not samples:
        raise TalkCutError("音轨是空的。")
    return samples


def extract_wav(ffmpeg: str, source: Path, dest: Path, sample_rate: int = 16000) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            ffmpeg,
            "-y",
            "-v",
            "error",
            "-i",
            str(source),
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            str(dest),
        ]
    )
