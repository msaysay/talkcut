"""One demo that walks every layout, in vertical and in landscape."""

from __future__ import annotations

import shutil
from pathlib import Path

from engine.cutout import build_person_webm
from engine.errors import TalkCutError
from engine.font_setup import ensure_fonts
from engine.motion import copy_role_fonts, detected_models, load_preset, render_with_props
from engine.runtime import require_ffmpeg
from engine.safe_zones import choose_anchor, detect_safe_zones, face_at, write_safe_zones

VERTICAL = [
    ("v1", "人脸全屏", "顶部标题带", "先把三秒说清"),
    ("v2", "知识窗口", "左上圆形画中画", "3 个要点"),
    ("v3", "收到角落", "全屏收成圆角遮罩", "底部留出安全区"),
    ("v4", "上下分屏", "上半屏图文", "下半屏是人"),
    ("v5", "字在身后", "抠像之后字留在后面", "真正留下的是金句"),
    ("v6", "横屏条带", "横幅放进竖屏", "条带不挡字幕"),
]
LANDSCAPE = [
    ("h1", "三分之一", "人占一侧", "图文占三分之二"),
    ("h2", "左人右板", "右侧信息面板", "先看结论"),
    ("h3", "大画中画", "380 像素窗口", "3 个要点"),
    ("h4", "下三分之一", "全屏人脸加字幕条", "钩子留在条里"),
    ("h5", "缓慢推近", "强调处推近人脸", "真正的重点"),
]
SLICE = 1.35


def build_segments(orientation: str, zones: dict) -> list[dict]:
    rows = VERTICAL if orientation == "vertical" else LANDSCAPE
    segments = []
    for index, (layout, title, body, caption) in enumerate(rows):
        start = round(index * SLICE, 3)
        end = round(start + SLICE, 3)
        face = face_at(zones.get("samples") or [], (start + end) / 2)
        anchor = "middle" if layout == "v3" else "top" if layout == "h3" else choose_anchor(face)
        segments.append(
            {
                "layout": layout,
                "start": start,
                "end": end,
                "title": title,
                "body": body,
                "caption": caption,
                "captionAnchor": anchor,
                "face": face,
            }
        )
    return segments


def render_layout_reel(folder: Path, video: Path, orientation: str, preset_name: str) -> dict:
    if orientation not in {"vertical", "landscape"}:
        raise TalkCutError("--orientation 只能是 vertical 或 landscape。")
    folder = Path(folder).expanduser().resolve()
    video = Path(video).expanduser().resolve()
    if not video.is_file():
        raise TalkCutError(f"找不到样片：{video}")
    preset = load_preset(preset_name)
    frames = (preset.get("frames") or {}).get(orientation) or (
        {"width": 1080, "height": 1920} if orientation == "vertical" else {"width": 1920, "height": 1080}
    )
    ffmpeg, _ffprobe = require_ffmpeg()
    rows = VERTICAL if orientation == "vertical" else LANDSCAPE
    duration = round(len(rows) * SLICE, 3)
    folder.mkdir(parents=True, exist_ok=True)
    models = detected_models()
    zones = detect_safe_zones(video, duration, models["face"], ffmpeg)
    write_safe_zones(zones, folder / "safe-zones.json")
    public = folder / "motion" / "public"
    if public.exists():
        shutil.rmtree(public)
    public.mkdir(parents=True)
    trimmed = public / "video.mp4"
    subprocess_trim(ffmpeg, video, trimmed, duration)
    person = None
    person_from = 0.0
    if orientation == "vertical":
        v5 = next(row for row in build_segments(orientation, zones) if row["layout"] == "v5")
        person_from = v5["start"]
        person = public / "person.mp4"
        from engine.font_setup import FONT_DIR

        gold = FONT_DIR / "NotoSerifSC-Black.ttf"
        build_person_webm(
            ffmpeg,
            video,
            v5["start"],
            v5["end"],
            models["segmenter"],
            person,
            label=v5["caption"],
            font_path=gold if gold.is_file() else None,
        )
    fonts = {}
    try:
        fonts = ensure_fonts()
    except TalkCutError:
        fonts = {}
    copy_role_fonts(public, fonts)
    from engine.beats import write_drum_bed

    write_drum_bed(public / "music.wav", duration, bpm=96)
    theme = dict(preset)
    theme["width"] = frames["width"]
    theme["height"] = frames["height"]
    segments = build_segments(orientation, zones)
    captions = []
    for segment in segments:
        captions.append(
            {
                "text": segment["caption"],
                "start": segment["start"],
                "end": segment["end"],
                "emphasis": "number" if "3" in segment["caption"] else ("gold" if "金句" in segment["caption"] or "真正" in segment["caption"] else "hook"),
                "keywords": ["3"] if "3" in segment["caption"] else [],
            }
        )
    props = {
        "durationInFrames": int(round(duration * 30)),
        "fps": 30,
        "width": frames["width"],
        "height": frames["height"],
        "orientation": orientation,
        "videoFile": "video.mp4",
        "musicFile": "music.wav",
        "fontFile": "fonts/fallback.ttf" if (public / "fonts" / "fallback.ttf").is_file() else "fonts/cjk.ttf",
        "fontFiles": {role: f"fonts/{role}.ttf" for role in fonts if (public / "fonts" / f"{role}.ttf").is_file()},
        "captions": captions,
        "beats": [round(i * 60 / 96, 3) for i in range(int(duration * 96 / 60) + 1)],
        "nameplate": None,
        "theme": theme,
        "title": segments[0]["title"],
        "segments": segments,
        "personFile": "person.mp4" if person else None,
        "personFrom": person_from,
        "safeZones": zones,
    }
    props_path = folder / "motion" / "props.json"
    props_path.parent.mkdir(parents=True, exist_ok=True)
    props_path.write_text(__import__("json").dumps(props, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out = folder / "export" / f"reel-{orientation}.mp4"
    render_with_props(preset["compositionId"], out, props_path, public)
    return {"movie": str(out), "orientation": orientation, "preset": preset["id"], "safeZones": str(folder / "safe-zones.json"), "layouts": [row[0] for row in rows]}


def subprocess_trim(ffmpeg: str, video: Path, dest: Path, duration: float) -> None:
    import subprocess

    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [ffmpeg, "-y", "-v", "error", "-i", str(video), "-t", f"{duration:.3f}", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(dest)],
        check=True,
        capture_output=True,
    )

