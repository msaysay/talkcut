"""Build Remotion props from a rough cut and render a vertical master."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from engine.beats import beats_from_bpm, detect_beats, write_drum_bed
from engine.errors import TalkCutError
from engine.media import load_pcm
from engine.pipeline import export_movie
from engine.runtime import require_ffmpeg
from engine.store import load, save

REPO = Path(__file__).resolve().parents[1]
PACK = REPO / "motion-pack"
PRESETS = PACK / "presets"
FONT_CANDIDATES = [
    Path("/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"),
    Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
]

CTA = re.compile(r"评论|私信|关注|预约|置顶")
NUMBER = re.compile(r"\d+|[零〇一二三四五六七八九十]+")
GOLD = re.compile(r"真正|往往|别再|金句")
LIST = re.compile(r"^(?:[1-9][.、]|第[一二三])")


def list_presets() -> list[dict]:
    found = []
    if not PRESETS.is_dir():
        return found
    for folder in sorted(PRESETS.iterdir()):
        config = folder / "preset.json"
        if folder.is_dir() and config.is_file():
            found.append(json.loads(config.read_text(encoding="utf-8")))
    return found


def load_preset(name: str) -> dict:
    for preset in list_presets():
        if preset.get("id") == name:
            return preset
    known = ", ".join(item["id"] for item in list_presets()) or "（无）"
    raise TalkCutError(f"没有预设 {name}。可选：{known}")


def keywords_in(text: str) -> list[str]:
    found = []
    for match in NUMBER.finditer(text):
        token = match.group(0)
        if token not in found:
            found.append(token)
    return found


def classify_caption(index: int, total: int, text: str, preset_id: str) -> str:
    if CTA.search(text) and not (index == 0 and total == 1):
        return "cta"
    if LIST.search(text):
        return "list"
    if index == 0:
        return "hook"
    if NUMBER.search(text):
        return "number"
    if GOLD.search(text) or (preset_id == "gold-line" and index == max(0, total // 2)):
        return "gold"
    return "body"


def captions_from_edit(project: dict, preset_id: str) -> list[dict]:
    edit = project.get("edit") or {}
    spans = edit.get("spans") or []
    if not spans:
        raise TalkCutError("还没有粗剪片段。先 apply，再做动效。")
    removed: dict[str, set[int]] = {}
    for entry in edit.get("removeWords") or []:
        removed.setdefault(entry["id"], set()).update(entry.get("indices") or [])
    segments = {segment["id"]: segment for segment in project["segments"]}
    clock = 0.0
    rows = []
    for span in spans:
        duration = max(0.0, float(span["end"]) - float(span["start"]))
        span_ids = [span["id"]] if span.get("id") else list(span.get("ids") or [])
        words = []
        for segment_id in span_ids:
            segment = segments.get(segment_id)
            if not segment:
                continue
            gone = removed.get(segment["id"], set())
            for index, word in enumerate(segment["words"]):
                if index in gone or word.get("kind") in {"breath", "silence", "filler"}:
                    continue
                if word["end"] <= span["start"] + 0.02 or word["start"] >= span["end"] - 0.02:
                    continue
                words.append(word)
        text = "".join(word["word"] for word in words) if words else str(span.get("text") or "")
        text = text.replace("〔气口〕", "").replace("〔静音〕", "").strip()
        if text and duration >= 0.04:
            rows.append({"text": text, "start": round(clock, 3), "end": round(clock + duration, 3)})
        clock += duration
    total = len(rows)
    captions = []
    for index, row in enumerate(rows):
        captions.append(
            {
                **row,
                "emphasis": classify_caption(index, total, row["text"], preset_id),
                "keywords": keywords_in(row["text"]),
            }
        )
    if not captions:
        raise TalkCutError("粗剪里没有可上屏的字幕。")
    return captions


def _find_font() -> Path:
    override = Path(__import__("os").environ["TALKCUT_FONT"]).expanduser() if __import__("os").environ.get("TALKCUT_FONT") else None
    candidates = [override] if override else []
    candidates.extend(FONT_CANDIDATES)
    for path in candidates:
        if path and path.is_file():
            return path
    raise TalkCutError("找不到中文字体。安装 fonts-droid-fallback，或设置 TALKCUT_FONT 指向一个 .ttf。")


def _music_track(folder: Path, duration: float, music: Path | None, bpm: float | None, ffmpeg: str) -> tuple[Path, list[float], float]:
    public = folder / "motion" / "public"
    public.mkdir(parents=True, exist_ok=True)
    target = public / "music.wav"
    if music is None:
        rate = bpm or 96
        beats = write_drum_bed(target, duration, bpm=rate)
        return target, beats, float(rate)
    source = Path(music).expanduser().resolve()
    if not source.is_file():
        raise TalkCutError(f"找不到配乐：{source}")
    shutil.copyfile(source, target)
    samples = load_pcm(ffmpeg, target)
    beats, detected = detect_beats(samples, bpm_hint=bpm)
    if bpm is None and beats:
        # Keep detection, but if the file is longer than the cut, trim the grid.
        beats = [beat for beat in beats if beat < duration]
    elif bpm:
        beats = beats_from_bpm(duration, bpm)
    return target, beats, float(detected)


def build_props(project: dict, preset: dict, beats: list[float], duration: float) -> dict:
    captions = captions_from_edit(project, preset["id"])
    nameplate = None
    settings = (project.get("edit") or {}).get("settings") or {}
    plate = (settings.get("credibilityNameplate") or {}).get("text") or ""
    if plate:
        nameplate = {"text": plate, "start": 0.2, "end": 3.2}
    fps = int(preset.get("fps") or 30)
    return {
        "durationInFrames": max(1, int(round(duration * fps))),
        "fps": fps,
        "videoFile": "video.mp4",
        "musicFile": "music.wav",
        "fontFile": "fonts/cjk.ttf",
        "captions": captions,
        "beats": beats,
        "nameplate": nameplate,
        "theme": preset,
        "title": captions[0]["text"][:18],
    }


def render_motion(
    folder: Path,
    preset_name: str,
    *,
    music: Path | None = None,
    bpm: float | None = None,
    lock: bool = False,
) -> dict:
    folder = Path(folder).expanduser().resolve()
    preset = load_preset(preset_name)
    ffmpeg, _ffprobe = require_ffmpeg()
    project = load(folder)
    if not (project.get("edit") or {}).get("applied"):
        raise TalkCutError("还没有粗剪。先 apply，再 motion。")
    export_dir = folder / "export"
    movie = export_dir / "final.mp4"
    if not movie.is_file():
        export_movie(folder)
    project = load(folder)
    duration = float((project.get("edit") or {}).get("export", {}).get("duration") or 0)
    if duration <= 0:
        spans = (project.get("edit") or {}).get("spans") or []
        duration = sum(float(span["end"]) - float(span["start"]) for span in spans)
    public = folder / "motion" / "public"
    if public.exists():
        shutil.rmtree(public)
    public.mkdir(parents=True)
    shutil.copyfile(movie, public / "video.mp4")
    font = _find_font()
    (public / "fonts").mkdir()
    shutil.copyfile(font, public / "fonts" / "cjk.ttf")
    _track, beats, detected_bpm = _music_track(folder, duration, music, bpm, ffmpeg)
    props = build_props(project, preset, beats, duration)
    props_path = folder / "motion" / "props.json"
    props_path.write_text(json.dumps(props, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out = export_dir / f"motion-{preset['id']}.mp4"
    _run_remotion("render", preset["compositionId"], out, props_path, public)
    still = None
    if preset.get("coverCompositionId"):
        still = export_dir / f"cover-{preset['id']}.png"
        _run_remotion("still", preset["coverCompositionId"], still, props_path, public)
    record = {
        "applied": True,
        "preset": preset["id"],
        "compositionId": preset["compositionId"],
        "props": str(props_path),
        "movie": str(out),
        "cover": str(still) if still else None,
        "bpm": detected_bpm,
        "beats": len(beats),
        "music": "generated-bed" if music is None else str(Path(music).resolve()),
        "ducking": True,
    }
    project = load(folder)
    project["motion"] = record
    if lock:
        approved = {
            "version": 1,
            "preset": preset["id"],
            "compositionId": preset["compositionId"],
            "lockedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        }
        (PRESETS / "approved.json").write_text(json.dumps(approved, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        record["locked"] = str(PRESETS / "approved.json")
        project["motion"] = record
    save(folder, project)
    return record


def render_cover_still(folder: Path, preset_name: str, title: str | None = None) -> dict:
    folder = Path(folder).expanduser().resolve()
    preset = load_preset(preset_name)
    props_path = folder / "motion" / "props.json"
    if not props_path.is_file():
        raise TalkCutError("还没有动效参数。先运行 motion。")
    props = json.loads(props_path.read_text(encoding="utf-8"))
    if title:
        props["title"] = title
        props_path.write_text(json.dumps(props, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    public = folder / "motion" / "public"
    dest = folder / "export" / f"cover-{preset['id']}.png"
    _run_remotion("still", preset.get("coverCompositionId") or "cover-still", dest, props_path, public)
    return {"cover": str(dest), "preset": preset["id"], "title": props.get("title")}


def _run_remotion(kind: str, composition: str, dest: Path, props_path: Path, public: Path) -> None:
    if not (PACK / "node_modules" / "remotion").is_dir():
        raise TalkCutError("motion-pack 依赖未安装。在 motion-pack/ 执行 npm install。")
    dest.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "npx",
        "--no-install",
        "remotion",
        kind,
        "src/index.ts",
        composition,
        str(dest),
        f"--props={props_path}",
        f"--public-dir={public}",
        "--overwrite",
    ]
    try:
        completed = subprocess.run(command, cwd=PACK, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired as exc:
        raise TalkCutError("Remotion 渲染超时。") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        tail = detail[-1200:] if detail else "无输出"
        raise TalkCutError(f"Remotion {kind} 失败：{tail}")
