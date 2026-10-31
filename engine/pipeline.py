"""import → read → propose → apply → export for one talking-head file."""

from __future__ import annotations

import json
from pathlib import Path

from engine.acoustic import words_from_pcm
from engine.asr import transcribe
from engine.covers import grab
from engine.cuts import excise_segment
from engine.errors import TalkCutError
from engine.finish import merge_spans, pack_delivery, render_mp4, write_srt
from engine.media import extract_wav, load_pcm, probe, sha256_file
from engine.planning import propose as build_proposal
from engine.runtime import require_ffmpeg
from engine.shared.speech_alignment import tighten_words
from engine.shared.speech_cleanup import plan_removals, word_reason
from engine.shared.smart_pauses import apply_pauses, detect as detect_pauses
from engine.store import load, revision_of, save

SAMPLE_RATE = 16000


def import_media(
    video: Path,
    folder: Path,
    *,
    transcript: Path | None = None,
    asr: str = "energy",
    whisper_model: str = "small",
) -> dict:
    if asr not in {"energy", "whisper"}:
        raise TalkCutError("--asr 只能是 energy 或 whisper。")
    ffmpeg, ffprobe = require_ffmpeg()
    source = Path(video).expanduser().resolve()
    if not source.is_file():
        raise TalkCutError(f"找不到原片：{source}")
    folder = Path(folder).expanduser().resolve()
    if folder.exists() and any(folder.iterdir()):
        raise TalkCutError("工程目录必须是空的。")
    folder.mkdir(parents=True, exist_ok=True)
    info = probe(ffprobe, source)
    if not info["hasAudio"]:
        raise TalkCutError("原片没有音轨。")
    wav = folder / "source.wav"
    extract_wav(ffmpeg, source, wav)
    samples = load_pcm(ffmpeg, wav, SAMPLE_RATE)
    pcm_duration = round(len(samples) / SAMPLE_RATE, 3)
    if transcript is not None:
        words = _load_transcript(Path(transcript))
        asr_name = "transcript"
        words = tighten_words(words, samples, SAMPLE_RATE)
    elif asr == "whisper":
        words = transcribe(wav, whisper_model)
        asr_name = "faster-whisper"
        words = tighten_words(words, samples, SAMPLE_RATE)
    else:
        words = words_from_pcm(samples, SAMPLE_RATE)
        asr_name = "energy"
    if not words:
        raise TalkCutError("没有得到任何词或声音片段。")
    for word in words:
        word["kind"] = word_reason(word) or word.get("kind") or "speech"
    project = {
        "version": 1,
        "source": {
            "path": str(source),
            "sha256": sha256_file(source),
            "duration": round(max(info["duration"], pcm_duration), 3),
            "pcmDuration": pcm_duration,
            "width": info["width"],
            "height": info["height"],
            "hasVideo": info["hasVideo"],
        },
        "wav": "source.wav",
        "asr": asr_name,
        "whisperModel": whisper_model if asr_name == "faster-whisper" else None,
        "segments": _group_segments(words),
        "plan": None,
        "edit": None,
        "motion": None,
    }
    project["revision"] = revision_of(project)
    save(folder, project)
    return _public(project)


def read_project(folder: Path) -> dict:
    return _public(load(Path(folder).expanduser().resolve()))


def propose(folder: Path) -> dict:
    folder = Path(folder).expanduser().resolve()
    project = load(folder)
    proposal = build_proposal(project)
    (folder / "proposal.json").write_text(json.dumps(proposal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    project["plan"] = {"proposal": "proposal.json", "selected": None}
    save(folder, project)
    return proposal


def choose_plan(folder: Path, direction_id: str) -> dict:
    folder = Path(folder).expanduser().resolve()
    project = load(folder)
    proposal_path = folder / "proposal.json"
    if not proposal_path.is_file():
        raise TalkCutError("还没有方案。先运行 propose。")
    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    match = next((item for item in proposal["directions"] if item["id"] == direction_id), None)
    if match is None:
        raise TalkCutError(f"方案里没有方向 {direction_id}。")
    project["plan"] = {"proposal": "proposal.json", "selected": direction_id}
    save(folder, project)
    return {"selected": direction_id, "revision": project["revision"], "title": match["title"]}


def apply_edit(folder: Path, changes: dict) -> dict:
    if changes.get("confirmed") is not True:
        raise TalkCutError("apply 需要 changes.confirmed = true，表示用户已经确认这份粗剪。propose 不会出片。")
    folder = Path(folder).expanduser().resolve()
    ffmpeg, _ffprobe = require_ffmpeg()
    project = load(folder)
    if changes.get("revision") != project["revision"]:
        raise TalkCutError("revision 已过期。重新 read，用新的 revision 再 apply。")
    summary = changes.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        raise TalkCutError("changes.summary 需要一段说明。")
    by_id = {segment["id"]: segment for segment in project["segments"]}
    order = changes.get("order") or [segment["id"] for segment in project["segments"]]
    if not isinstance(order, list) or any(not isinstance(item, str) or item not in by_id for item in order) or len(order) != len(set(order)):
        raise TalkCutError("order 里的片段 id 无效或重复。")
    dropped = {item["id"] for item in changes.get("removeSpans") or []}
    unknown = dropped - set(by_id)
    if unknown:
        raise TalkCutError(f"removeSpans 有未知片段：{sorted(unknown)}")
    keep_ids = set()
    for item in changes.get("keepHumanMoments") or []:
        if not isinstance(item, dict) or item.get("id") not in by_id:
            raise TalkCutError("keepHumanMoments 需要现有片段 id。")
        keep_ids.add(item["id"])
    removed = {segment["id"]: set() for segment in project["segments"]}
    explicit = _explicit_words(changes.get("removeWords") or [], by_id)
    for item in explicit:
        removed[item["id"]].update(item["indices"])
    cleanup = changes.get("cleanup") or {}
    automatic = plan_removals(project["segments"], cleanup, keep_ids)
    for item in automatic:
        if item["id"] not in dropped:
            removed[item["id"]].update(item["indices"])
    spans = []
    for segment_id in order:
        if segment_id in dropped:
            continue
        spans.extend(excise_segment(by_id[segment_id], removed[segment_id]))
    spans = _apply_pause_detector(folder, project, spans, removed, ffmpeg)
    spans = merge_spans(spans)
    project["edit"] = {
        "applied": True,
        "summary": summary.strip(),
        "revision": project["revision"],
        "confirmed": True,
        "order": order,
        "removeSpans": changes.get("removeSpans") or [],
        "removeWords": explicit + automatic,
        "keepHumanMoments": changes.get("keepHumanMoments") or [],
        "cleanup": cleanup,
        "settings": changes.get("settings") or {},
        "spans": spans,
    }
    save(folder, project)
    return {
        "revision": project["revision"],
        "spans": spans,
        "removedWords": len(explicit) + len(automatic),
        "durationKept": round(sum(span["end"] - span["start"] for span in spans), 3),
    }


def export_movie(folder: Path) -> dict:
    folder = Path(folder).expanduser().resolve()
    ffmpeg, ffprobe = require_ffmpeg()
    project = load(folder)
    edit = project.get("edit") or {}
    if not edit.get("applied"):
        raise TalkCutError("还没有粗剪。先 apply，再 export。")
    source = Path(project["source"]["path"])
    if not source.is_file() or sha256_file(source) != project["source"]["sha256"]:
        raise TalkCutError("原片缺失或已变化，拒绝导出。")
    spans = edit.get("spans") or []
    dest_dir = folder / "export"
    dest_dir.mkdir(parents=True, exist_ok=True)
    movie = dest_dir / "final.mp4"
    playback = (edit.get("settings") or {}).get("speed", 1)
    rendered = render_mp4(ffmpeg, ffprobe, source, spans, movie, playback)
    write_srt(spans, dest_dir / "captions.srt")
    (dest_dir / "project.json").write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    archive = pack_delivery(dest_dir, movie)
    project["edit"]["export"] = {"movie": str(movie), "bundle": str(archive), "duration": rendered["duration"]}
    save(folder, project)
    return {"movie": str(movie), "bundle": str(archive), "duration": rendered["duration"], "spans": len(spans)}


def cover_frame(folder: Path) -> dict:
    folder = Path(folder).expanduser().resolve()
    ffmpeg, _ffprobe = require_ffmpeg()
    project = load(folder)
    edit = project.get("edit") or {}
    spans = edit.get("spans") or []
    if not spans:
        raise TalkCutError("还没有粗剪片段，不能抽封面。")
    if not project["source"]["hasVideo"]:
        raise TalkCutError("原片没有画面，封面帧需要视频。")
    span = spans[0]
    at = min(span["end"] - 0.02, span["start"] + 0.08)
    dest = folder / "export" / "cover.jpg"
    grab(ffmpeg, Path(project["source"]["path"]), max(span["start"], at), dest)
    return {"cover": str(dest), "sourceTime": round(max(span["start"], at), 3)}


def motion_hook(folder: Path) -> dict:
    folder = Path(folder).expanduser().resolve()
    project = load(folder)
    project["motion"] = {
        "pack": "motion-pack",
        "applied": False,
        "presets": "motion-pack/presets",
        "note": "本轮导出不经过 Remotion。模板仍应在认可后锁进 presets/approved.json。",
    }
    save(folder, project)
    return project["motion"]


def _load_transcript(path: Path) -> list[dict]:
    if not path.is_file():
        raise TalkCutError(f"找不到文稿：{path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("words")
    if rows is None and payload.get("segments"):
        rows = [word for segment in payload["segments"] for word in segment.get("words", [])]
    if not isinstance(rows, list) or not rows:
        raise TalkCutError("文稿需要 words 数组，每项含 word/start/end。")
    words = []
    for row in rows:
        if not isinstance(row, dict) or "word" not in row:
            raise TalkCutError("文稿里有不完整的词。")
        start, end = float(row["start"]), float(row["end"])
        if end <= start:
            raise TalkCutError(f"词「{row['word']}」的时间无效。")
        words.append({"word": str(row["word"]).strip(), "start": round(start, 3), "end": round(end, 3)})
    return words


def _group_segments(words: list[dict]) -> list[dict]:
    groups: list[list[dict]] = []
    current: list[dict] = []
    for word in words:
        long_silence = word.get("kind") == "silence" and word["end"] - word["start"] >= 0.45
        if long_silence:
            if current:
                groups.append(current)
                current = []
            groups.append([word])
        else:
            current.append(word)
    if current:
        groups.append(current)
    segments = []
    for index, group in enumerate(groups, start=1):
        segments.append(
            {
                "id": f"s{index}",
                "start": group[0]["start"],
                "end": group[-1]["end"],
                "text": "".join(word["word"] for word in group),
                "deleted": False,
                "removed": [],
                "words": group,
            }
        )
    return segments


def _explicit_words(entries: list, by_id: dict) -> list[dict]:
    planned = []
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("id") not in by_id or not isinstance(entry.get("indices"), list):
            raise TalkCutError("removeWords 需要片段 id 和 indices。")
        segment = by_id[entry["id"]]
        indices = []
        for index in entry["indices"]:
            if type(index) is not int or not 0 <= index < len(segment["words"]):
                raise TalkCutError("removeWords.indices 超出该片段。")
            indices.append(index)
        quote = "".join(segment["words"][index]["word"] for index in indices)
        if "quote" in entry and entry["quote"] != quote:
            raise TalkCutError(f"removeWords 引用和原词不一致：期望「{quote}」。")
        planned.append(
            {
                "id": entry["id"],
                "indices": indices,
                "quote": quote,
                "reason": entry.get("reason") or "filler",
                "automatic": False,
            }
        )
    return planned


def _apply_pause_detector(folder: Path, project: dict, spans: list[dict], removed: dict, ffmpeg: str) -> list[dict]:
    if not spans:
        return []
    speech_words = []
    for segment in project["segments"]:
        gone = removed.get(segment["id"], set())
        for index, word in enumerate(segment["words"]):
            if index in gone or word.get("kind") in {"breath", "silence", "filler"}:
                continue
            speech_words.append(word)
    record = {
        "video_path": str(folder / project["wav"]),
        "duration_seconds": max(project["source"]["duration"], max(span["end"] for span in spans)) + 0.05,
        "video_id": project["revision"][:16],
        "segments": [{"words": speech_words or [{"word": " ", "start": 0, "end": 0}]}],
    }
    # A zero-length placeholder would fail the pause guard. Skip detection then.
    if not speech_words:
        return spans
    receipt = detect_pauses(record, ffmpeg=ffmpeg, cache_dir=folder / ".cache")
    project["pauses"] = {
        "count": len(receipt["pauses"]),
        "thresholdDb": receipt.get("thresholdDb"),
        "pauses": receipt["pauses"],
    }
    source_rows = []
    clips = []
    for index, span in enumerate(spans):
        clip_id = f"c{index}"
        word = {"word": span.get("text") or "口", "start": span["start"], "end": span["end"]}
        source_rows.append({"id": clip_id, "words": [word]})
        clips.append(
            {
                "id": clip_id,
                "segmentId": span["id"],
                "start": span["start"],
                "end": span["end"],
                "firstIndex": 0,
                "lastIndex": 0,
                "text": span.get("text") or "",
            }
        )
    try:
        paused = apply_pauses(clips, source_rows, [row for row in receipt["pauses"] if not row.get("keep")])
    except ValueError as exc:
        raise TalkCutError(str(exc)) from exc
    return [
        {
            "id": item.get("segmentId", item["id"]),
            "start": round(float(item["start"]), 3),
            "end": round(float(item["end"]), 3),
            "text": item.get("text") or "",
        }
        for item in paused
        if float(item["end"]) - float(item["start"]) >= 0.04
    ]


def _public(project: dict) -> dict:
    return {
        "revision": project["revision"],
        "asr": project["asr"],
        "duration": project["source"]["duration"],
        "source": project["source"]["path"],
        "segments": [
            {
                "id": segment["id"],
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"],
                "words": segment["words"],
            }
            for segment in project["segments"]
        ],
        "plan": project.get("plan"),
        "editApplied": bool((project.get("edit") or {}).get("applied")),
    }
