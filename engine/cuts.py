"""Turn removed words into source time spans using the ported audio_cuts."""

from __future__ import annotations

import hashlib

from engine.errors import TalkCutError
from engine.shared.audio_cuts import apply_audio_cuts


def _merge(ranges: list[tuple[float, float]]) -> list[list[float]]:
    merged: list[list[float]] = []
    for start, end in sorted(ranges):
        if end - start < 0.001:
            continue
        if merged and start <= merged[-1][1] + 0.001:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged


def normalize_cuts(start: float, end: float, ranges: list[tuple[float, float]]) -> tuple[list[list[float]], list[tuple[float, float]]]:
    """Drop fragments shorter than 40 ms by folding them into the cut."""
    merged = _merge([(max(start, a), min(end, b)) for a, b in ranges])
    changed = True
    while changed:
        changed = False
        rebuilt: list[tuple[float, float]] = []
        cursor = start
        pieces: list[tuple[str, float, float]] = []
        for cut_start, cut_end in merged:
            if cut_start > cursor:
                pieces.append(("keep", cursor, cut_start))
            pieces.append(("cut", cut_start, cut_end))
            cursor = cut_end
        if end > cursor:
            pieces.append(("keep", cursor, end))
        for kind, piece_start, piece_end in pieces:
            if kind == "keep" and piece_end - piece_start < 0.04 - 1e-6:
                rebuilt.append((piece_start, piece_end))
                changed = True
            elif kind == "cut":
                rebuilt.append((piece_start, piece_end))
        merged = _merge(rebuilt)
    keeps: list[tuple[float, float]] = []
    cursor = start
    for cut_start, cut_end in merged:
        if cut_start > cursor + 1e-6:
            keeps.append((cursor, cut_start))
        cursor = max(cursor, cut_end)
    if end > cursor + 1e-6:
        keeps.append((cursor, end))
    keeps = [item for item in keeps if item[1] - item[0] >= 0.04 - 1e-6]
    return merged, keeps


def excise_segment(segment: dict, removed: set[int]) -> list[dict]:
    words = segment["words"]
    if not words:
        return []
    kept = [index for index in range(len(words)) if index not in removed]
    if not kept:
        return []
    start = float(words[0]["start"])
    end = float(words[-1]["end"])
    ranges = []
    for index in sorted(removed):
        word = words[index]
        ranges.append((float(word["start"]), float(word["end"])))
    cuts, keeps = normalize_cuts(start, end, ranges)
    if not keeps:
        return []
    if not cuts:
        return [_span(segment, start, end, kept)]
    clip = {
        "id": segment["id"],
        "start": start,
        "end": end,
        "firstIndex": 0,
        "lastIndex": len(words) - 1,
        "text": segment.get("text", ""),
    }
    payload = {}
    for cut_start, cut_end in cuts:
        overlaps_word = any(
            word["end"] > cut_start + 1e-6 and word["start"] < cut_end - 1e-6 for word in words
        )
        cut_id = hashlib.sha256(f"{segment['id']}:{cut_start:.3f}:{cut_end:.3f}".encode()).hexdigest()[:32]
        payload.setdefault(f"{segment['id']}:0:{len(words) - 1}", []).append(
            {"id": cut_id, "start": cut_start, "end": cut_end, "wordCut": overlaps_word}
        )
    try:
        pieces = apply_audio_cuts([clip], [segment], payload)
    except ValueError as exc:
        raise TalkCutError(str(exc)) from exc
    return [
        {
            "id": segment["id"],
            "start": round(piece["start"], 3),
            "end": round(piece["end"], 3),
            "text": piece.get("text") or "",
        }
        for piece in pieces
    ]


def _span(segment: dict, start: float, end: float, kept: list[int]) -> dict:
    text = "".join(segment["words"][index]["word"] for index in kept)
    return {"id": segment["id"], "start": round(start, 3), "end": round(end, 3), "text": text}
