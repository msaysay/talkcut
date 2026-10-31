"""Render a playable mp4 from kept source spans.

Sayframe's editor_export.bundle packs the result. Typography covers stay optional;
this path does not need Remotion or a font.
"""

from __future__ import annotations

from pathlib import Path

from engine.errors import TalkCutError
from engine.media import probe, run
from engine.shared.editor_export import bundle
from engine.shared.render_spans import render_spans
from engine.shared.video_finish import speed


def merge_spans(spans: list[dict]) -> list[dict]:
    clips = [dict(span) for span in spans]
    grouped = render_spans(clips)
    merged = []
    for group in grouped:
        members = [clips[index] for index in group["indices"]]
        merged.append(
            {
                "start": group["start"],
                "end": group["end"],
                "text": "".join(item.get("text") or "" for item in members),
                "ids": [item["id"] for item in members],
            }
        )
    return merged


def write_srt(spans: list[dict], dest: Path) -> None:
    clock = 0.0
    lines = []
    for index, span in enumerate(spans, start=1):
        length = max(0.0, span["end"] - span["start"])
        text = (span.get("text") or "").strip()
        if text and length > 0:
            lines.append(str(index))
            lines.append(f"{_srt(clock)} --> {_srt(clock + length)}")
            lines.append(text)
            lines.append("")
        clock += length
    dest.write_text("\n".join(lines), encoding="utf-8")


def _srt(value: float) -> str:
    total = max(0, int(round(value * 1000)))
    hours, total = divmod(total, 3_600_000)
    minutes, total = divmod(total, 60_000)
    seconds, millis = divmod(total, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"


def render_mp4(ffmpeg: str, ffprobe: str, source: Path, spans: list[dict], dest: Path, playback_speed: float = 1) -> dict:
    if not spans:
        raise TalkCutError("没有可导出的片段。")
    rate = speed(playback_speed)
    info = probe(ffprobe, source)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if info["hasVideo"]:
        _render_av(ffmpeg, source, spans, dest, rate)
    else:
        _render_audio_only(ffmpeg, source, spans, dest, rate, info["duration"])
    rendered = probe(ffprobe, dest)
    return {"path": str(dest), "duration": round(rendered["duration"], 3), "speed": rate}


def _render_av(ffmpeg: str, source: Path, spans: list[dict], dest: Path, rate: float) -> None:
    chains, labels = _chains(spans, rate, with_video=True)
    chains.append("".join(labels) + f"concat=n={len(spans)}:v=1:a=1[outv][outa]")
    run(
        [
            ffmpeg,
            "-y",
            "-v",
            "error",
            "-i",
            str(source),
            "-filter_complex",
            ";".join(chains),
            "-map",
            "[outv]",
            "-map",
            "[outa]",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            str(dest),
        ],
        timeout=300,
    )


def _render_audio_only(ffmpeg: str, source: Path, spans: list[dict], dest: Path, rate: float, duration: float) -> None:
    chains, labels = _chains(spans, rate, with_video=False)
    chains.append("".join(labels) + f"concat=n={len(spans)}:v=0:a=1[outa]")
    run(
        [
            ffmpeg,
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"color=c=0x141414:s=640x360:r=25:d={max(duration, 1):.3f}",
            "-i",
            str(source),
            "-filter_complex",
            ";".join(chains),
            "-map",
            "[0:v]",
            "-map",
            "[outa]",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(dest),
        ],
        timeout=300,
    )


def _chains(spans: list[dict], rate: float, *, with_video: bool) -> tuple[list[str], list[str]]:
    chains: list[str] = []
    labels: list[str] = []
    video_speed = f",setpts=PTS/{rate}" if rate != 1 else ""
    audio_speed = f",atempo={rate}" if rate != 1 else ""
    media = "0" if with_video else "1"
    for index, span in enumerate(spans):
        start = f"{span['start']:.3f}"
        end = f"{span['end']:.3f}"
        if with_video:
            chains.append(f"[{media}:v]trim=start={start}:end={end},setpts=PTS-STARTPTS{video_speed}[v{index}]")
            labels.append(f"[v{index}]")
        chains.append(f"[{media}:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS{audio_speed}[a{index}]")
        labels.append(f"[a{index}]")
    return chains, labels


def pack_delivery(folder: Path, movie: Path) -> Path:
    return bundle(folder, movie)
