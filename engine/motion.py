"""Build Remotion props from a rough cut and render a vertical master."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from engine.beats import beats_from_bpm, detect_beats
from engine.errors import TalkCutError
from engine.media import load_pcm, probe
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
PHRASE_LIMIT = 18
MIN_PHRASE = 0.04
PHRASE_BREAK = re.compile(r"[，。！？、；,.!?\n]|…+|——+|—+|～+")


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


def _phrase_parts(text: str) -> list[str]:
    raw = [part.strip() for part in PHRASE_BREAK.split(text) if part and part.strip()]
    if not raw and text.strip():
        raw = [text.strip()]
    parts: list[str] = []
    for chunk in raw:
        if len(chunk) <= PHRASE_LIMIT:
            parts.append(chunk)
        else:
            parts.extend(chunk[index : index + PHRASE_LIMIT] for index in range(0, len(chunk), PHRASE_LIMIT))
    return parts


def _coalesce(parts: list[str], count: int) -> list[str]:
    if count <= 1 or not parts:
        return ["".join(parts)] if parts else []
    total = sum(len(part) for part in parts)
    target = total / count
    groups: list[str] = []
    buffer = ""
    filled = 0
    for part in parts:
        if buffer and filled >= target and len(groups) < count - 1:
            groups.append(buffer)
            buffer = part
            filled = len(part)
        else:
            buffer += part
            filled += len(part)
    if buffer:
        groups.append(buffer)
    while len(groups) > count:
        groups[-2] += groups[-1]
        groups.pop()
    return groups


def _unoverlap(pieces: list[dict]) -> list[dict]:
    cleaned: list[dict] = []
    for piece in pieces:
        start = float(piece["start"])
        end = float(piece["end"])
        if cleaned and start < float(cleaned[-1]["end"]):
            start = float(cleaned[-1]["end"])
        if end - start < MIN_PHRASE:
            continue
        item = dict(piece)
        item["start"] = round(start, 3)
        item["end"] = round(end, 3)
        if item["end"] <= item["start"]:
            continue
        cleaned.append(item)
    return cleaned


def split_caption_phrases(captions: list[dict]) -> list[dict]:
    """Split plan and edit captions on punctuation, pauses, and length.

    Each piece keeps a slice of the parent interval. Adjacent pieces never overlap.
    """
    pieces: list[dict] = []
    for caption in captions:
        text = str(caption.get("text") or "").strip()
        start = float(caption["start"])
        end = float(caption["end"])
        span = end - start
        if not text or span < MIN_PHRASE:
            continue
        parts = _phrase_parts(text)
        if not parts:
            continue
        max_parts = max(1, int(span / MIN_PHRASE))
        if len(parts) > max_parts:
            parts = _coalesce(parts, max_parts)
        weights = [max(1, len(part)) for part in parts]
        total = sum(weights)
        cursor = start
        for index, (part, weight) in enumerate(zip(parts, weights)):
            piece_end = end if index == len(parts) - 1 else cursor + span * weight / total
            keywords = [token for token in (caption.get("keywords") or []) if token and token in part]
            pieces.append({**caption, "text": part, "start": cursor, "end": piece_end, "keywords": keywords})
            cursor = piece_end
    return _unoverlap(pieces)


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
    captions = split_caption_phrases(captions)
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


def _music_track(
    folder: Path, duration: float, music: Path | None, bpm: float | None, ffmpeg: str
) -> tuple[Path | None, list[float], float | None]:
    public = folder / "motion" / "public"
    public.mkdir(parents=True, exist_ok=True)
    if music is None:
        if bpm:
            return None, beats_from_bpm(duration, bpm), float(bpm)
        return None, [], None
    target = public / "music.wav"
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


def apply_orientation(preset: dict, orientation: str) -> dict:
    if orientation not in {"vertical", "landscape"}:
        raise TalkCutError("--orientation 只能是 vertical 或 landscape。")
    themed = dict(preset)
    frames = (preset.get("frames") or {}).get(orientation)
    if frames:
        themed["width"] = frames["width"]
        themed["height"] = frames["height"]
    elif orientation == "landscape":
        themed["width"] = 1920
        themed["height"] = 1080
    return themed


def detected_models() -> dict[str, Path]:
    folder = REPO / "runtime" / "models"
    face = folder / "blaze_face_short_range.tflite"
    segmenter = folder / "selfie_segmenter.tflite"
    if not face.is_file() or not segmenter.is_file():
        raise TalkCutError("缺少 MediaPipe 模型。运行 python3 pipeline/cli/talkcut.py setup --vision")
    return {"face": face, "segmenter": segmenter}


def copy_role_fonts(public: Path, fonts: dict[str, Path]) -> dict[str, str]:
    dest = public / "fonts"
    dest.mkdir(parents=True, exist_ok=True)
    written = {}
    for role, path in fonts.items():
        if path.is_file():
            shutil.copyfile(path, dest / f"{role}.ttf")
            written[role] = f"fonts/{role}.ttf"
    fallback = dest / "fallback.ttf"
    cjk = dest / "cjk.ttf"
    if fallback.is_file():
        shutil.copyfile(fallback, cjk)
    elif not cjk.is_file():
        system = _find_font()
        shutil.copyfile(system, cjk)
        if "fallback" not in written:
            shutil.copyfile(system, fallback)
            written["fallback"] = "fonts/fallback.ttf"
    return written


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
        "width": int(preset.get("width") or 1080),
        "height": int(preset.get("height") or 1920),
        "orientation": "landscape" if int(preset.get("width") or 1080) > int(preset.get("height") or 1920) else "vertical",
        "videoFile": "video.mp4",
        "musicFile": None,
        "fontFile": "fonts/cjk.ttf",
        "fontFiles": {},
        "captions": captions,
        "beats": beats,
        "nameplate": nameplate,
        "theme": preset,
        "title": captions[0]["text"][:18],
        "segments": [],
        "personFile": None,
        "personFrom": 0,
    }


def plan_path_for(folder: Path, orientation: str) -> Path | None:
    sided = folder / f"layout-plan-{orientation}.json"
    if sided.is_file():
        return sided
    generic = folder / "layout-plan.json"
    if not generic.is_file():
        return None
    payload = json.loads(generic.read_text(encoding="utf-8"))
    if payload.get("orientation") in (None, orientation):
        return generic
    return None


def segments_from_plan(plan: dict, zones: dict | None = None) -> tuple[list[dict], list[dict]]:
    from engine.safe_zones import choose_anchor, face_at

    segments = []
    captions = []
    samples = (zones or {}).get("samples") or []
    for item in plan["items"]:
        face = face_at(samples, (item["start"] + item["end"]) / 2) if samples else None
        if item["layout"] == "v3":
            anchor = "middle"
        elif item["layout"] == "h3":
            anchor = "top"
        else:
            anchor = choose_anchor(face) if face else "bottom"
        segments.append(
            {
                "layout": item["layout"],
                "start": item["start"],
                "end": item["end"],
                "title": item.get("roleLabel") or item["layout"],
                "body": "",
                "caption": item["text"],
                "captionAnchor": anchor,
                "face": face,
            }
        )
        captions.append(
            {
                "text": item["text"],
                "start": item["start"],
                "end": item["end"],
                "emphasis": item.get("emphasis") or "body",
                "keywords": item.get("keywords") or [],
                "font": item.get("font") or "body",
                "effects": item.get("effects") or [],
            }
        )
    return segments, split_caption_phrases(captions)


def render_from_plan(
    folder: Path,
    plan_path: Path,
    preset_name: str,
    *,
    music: Path | None = None,
    bpm: float | None = None,
    lock: bool = False,
    orientation: str = "vertical",
) -> dict:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if plan.get("orientation") != orientation:
        raise TalkCutError("layout-plan.json 的画幅和 --orientation 不一致。请按这个画幅重新 plan。")
    video = Path(plan.get("video") or "")
    if not video.is_file():
        raise TalkCutError("计划里的视频不存在。plan 时加上 --video，或改 layout-plan.json 里的 video。")
    preset = apply_orientation(load_preset(preset_name), orientation)
    ffmpeg, ffprobe = require_ffmpeg()
    duration = float(plan["duration"])
    public = folder / "motion" / "public"
    if public.exists():
        shutil.rmtree(public)
    public.mkdir(parents=True)
    trimmed = public / "video.mp4"
    info = probe(ffprobe, video)
    command = [
        ffmpeg,
        "-y",
        "-v",
        "error",
        "-i",
        str(video),
        "-t",
        f"{duration:.3f}",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
    ]
    if info["hasAudio"]:
        command.extend(["-c:a", "aac", "-b:a", "160k"])
    command.append(str(trimmed))
    subprocess.run(command, check=True, capture_output=True)
    zones = None
    try:
        models = detected_models()
        from engine.safe_zones import detect_safe_zones, write_safe_zones

        zones = detect_safe_zones(trimmed, duration, models["face"], ffmpeg)
        write_safe_zones(zones, folder / "safe-zones.json")
    except TalkCutError:
        models = None
    segments, captions = segments_from_plan(plan, zones)
    person_file = None
    person_from = 0.0
    v5 = [item for item in plan["items"] if item["layout"] == "v5"]
    if v5 and models:
        from engine.cutout import build_person_webm
        from engine.font_setup import FONT_DIR

        person_from = float(v5[0]["start"])
        person_file = public / "person.mp4"
        gold = FONT_DIR / "NotoSerifSC-Black.ttf"
        build_person_webm(
            ffmpeg,
            trimmed,
            person_from,
            float(v5[-1]["end"]),
            models["segmenter"],
            person_file,
            label=v5[0]["text"],
            font_path=gold if gold.is_file() else None,
        )
    try:
        from engine.font_setup import ensure_fonts

        role_fonts = ensure_fonts()
    except TalkCutError:
        role_fonts = {}
    font_files = copy_role_fonts(public, role_fonts)
    track, music_beats, detected = _music_track(folder, duration, music, bpm, ffmpeg)
    rate = detected or bpm or float(plan.get("bpm") or 96)
    fps = int(preset.get("fps") or 30)
    props = {
        "durationInFrames": max(1, int(round(duration * fps))),
        "fps": fps,
        "width": int(preset.get("width") or 1080),
        "height": int(preset.get("height") or 1920),
        "orientation": orientation,
        "videoFile": "video.mp4",
        "musicFile": "music.wav" if track else None,
        "fontFile": font_files.get("fallback") or "fonts/cjk.ttf",
        "fontFiles": font_files,
        "captions": captions,
        "beats": plan.get("beats") or music_beats or beats_from_bpm(duration, rate),
        "nameplate": None,
        "theme": preset,
        "title": (captions[0]["text"][:18] if captions else preset.get("name") or ""),
        "segments": segments,
        "personFile": "person.mp4" if person_file else None,
        "personFrom": person_from,
    }
    props_path = folder / "motion" / "props.json"
    props_path.write_text(json.dumps(props, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    export_dir = folder / "export"
    out = export_dir / f"motion-{preset['id']}{'' if orientation == 'vertical' else '-landscape'}.mp4"
    _run_remotion("render", preset["compositionId"], out, props_path, public, crf=28)
    record = {
        "applied": True,
        "fromPlan": str(plan_path),
        "preset": preset["id"],
        "movie": str(out),
        "orientation": orientation,
        "width": props["width"],
        "height": props["height"],
    }
    if (folder / "project.json").is_file():
        project = load(folder)
        project["motion"] = record
        save(folder, project)
    if lock:
        approved = {
            "version": 1,
            "preset": preset["id"],
            "lockedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        }
        (PRESETS / "approved.json").write_text(json.dumps(approved, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return record


def render_motion(
    folder: Path,
    preset_name: str,
    *,
    music: Path | None = None,
    bpm: float | None = None,
    lock: bool = False,
    orientation: str = "vertical",
    layout: str | None = None,
) -> dict:
    folder = Path(folder).expanduser().resolve()
    planned = plan_path_for(folder, orientation)
    if planned and layout is None:
        return render_from_plan(
            folder,
            planned,
            preset_name,
            music=music,
            bpm=bpm,
            lock=lock,
            orientation=orientation,
        )
    preset = apply_orientation(load_preset(preset_name), orientation)
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
    try:
        from engine.font_setup import ensure_fonts

        role_fonts = ensure_fonts()
    except TalkCutError:
        role_fonts = {}
    font_files = copy_role_fonts(public, role_fonts)
    track, beats, detected_bpm = _music_track(folder, duration, music, bpm, ffmpeg)
    props = build_props(project, preset, beats, duration)
    props["musicFile"] = "music.wav" if track else None
    props["fontFiles"] = font_files
    if font_files.get("fallback"):
        props["fontFile"] = font_files["fallback"]
    if layout:
        props["segments"] = [
            {
                "layout": layout,
                "start": 0,
                "end": round(duration, 3),
                "title": props["title"],
                "body": "",
                "caption": props["captions"][0]["text"] if props["captions"] else "",
                "captionAnchor": "bottom",
                "face": None,
            }
        ]
    props_path = folder / "motion" / "props.json"
    props_path.write_text(json.dumps(props, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out = export_dir / f"motion-{preset['id']}{'' if orientation == 'vertical' else '-landscape'}.mp4"
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
        "orientation": orientation,
        "width": preset.get("width"),
        "height": preset.get("height"),
        "beats": len(beats),
        "music": None if track is None else str(Path(music).resolve()),
        "ducking": track is not None,
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


def render_with_props(composition: str, dest: Path, props_path: Path, public: Path) -> None:
    _run_remotion("render", composition, dest, props_path, public)


def _run_remotion(kind: str, composition: str, dest: Path, props_path: Path, public: Path, crf: int | None = None) -> None:
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
    if crf is not None and kind == "render":
        command.append(f"--crf={crf}")
    try:
        completed = subprocess.run(command, cwd=PACK, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired as exc:
        raise TalkCutError("Remotion 渲染超时。") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        tail = detail[-1200:] if detail else "无输出"
        raise TalkCutError(f"Remotion {kind} 失败：{tail}")
