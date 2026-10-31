"""Build a short talking-head stand-in: tones, a breath, and silence."""

from __future__ import annotations

import array
import math
import wave
from pathlib import Path

from engine.media import run

SAMPLE_RATE = 16000


def _tone(frequency: float, duration: float, amplitude: float) -> list[int]:
    count = int(round(duration * SAMPLE_RATE))
    return [
        int(max(-32767, min(32767, amplitude * 32767 * math.sin(2 * math.pi * frequency * index / SAMPLE_RATE))))
        for index in range(count)
    ]


def _silence(duration: float) -> list[int]:
    return [0] * int(round(duration * SAMPLE_RATE))


def _write_wav(path: Path, samples: list[int]) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(array.array("h", samples).tobytes())


def _mux(ffmpeg: str, wav: Path, mp4: Path, duration: float) -> None:
    run(
        [
            ffmpeg,
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"color=c=0x203040:s=640x360:r=25:d={duration + 0.2:.3f}",
            "-i",
            str(wav),
            "-map",
            "0:v",
            "-map",
            "1:a",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "pcm_s16le",
            str(mp4),
        ]
    )


def make_breath_demo(folder: Path, ffmpeg: str) -> dict:
    """Speech tones separated by silence and one low breath. No spoken words."""
    pieces = [
        ("speech", _tone(440, 0.50, 0.35)),
        ("silence", _silence(0.80)),
        ("speech", _tone(880, 0.46, 0.35)),
        ("breath", _tone(80, 0.30, 0.012)),
        ("speech", _tone(660, 0.50, 0.35)),
        ("silence", _silence(1.00)),
    ]
    samples: list[int] = []
    regions = []
    for kind, block in pieces:
        start = len(samples) / SAMPLE_RATE
        samples.extend(block)
        regions.append({"kind": kind, "start": round(start, 3), "end": round(len(samples) / SAMPLE_RATE, 3)})
    folder.mkdir(parents=True, exist_ok=True)
    wav = folder / "breath-demo.wav"
    mp4 = folder / "breath-demo.mp4"
    _write_wav(wav, samples)
    _mux(ffmpeg, wav, mp4, len(samples) / SAMPLE_RATE)
    return {"wav": wav, "video": mp4, "regions": regions, "duration": round(len(samples) / SAMPLE_RATE, 3)}


def make_filler_demo(folder: Path, ffmpeg: str) -> dict:
    """Three loud tones. The middle one is the filler word 嗯 and must be cut by text, not loudness."""
    pieces = [
        ("今天", _tone(520, 0.40, 0.35)),
        ("嗯", _tone(300, 0.24, 0.35)),
        ("清楚", _tone(700, 0.40, 0.35)),
    ]
    samples: list[int] = []
    words = []
    for text, block in pieces:
        start = len(samples) / SAMPLE_RATE
        samples.extend(block)
        end = len(samples) / SAMPLE_RATE
        words.append({"word": text, "start": round(start, 3), "end": round(end, 3)})
    folder.mkdir(parents=True, exist_ok=True)
    wav = folder / "filler-demo.wav"
    mp4 = folder / "filler-demo.mp4"
    _write_wav(wav, samples)
    _mux(ffmpeg, wav, mp4, len(samples) / SAMPLE_RATE)
    transcript = folder / "filler-words.json"
    transcript.write_text(
        __import__("json").dumps({"words": words}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {"video": mp4, "transcript": transcript, "words": words, "duration": round(len(samples) / SAMPLE_RATE, 3)}
