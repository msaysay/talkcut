"""Portable timing helpers from sayframe speech_alignment.

Upstream revise() called a machine-local SenseVoice or Whisper install and is
not ported. TalkCut transcribes with engine.asr (opt-in) or engine.acoustic.
"""

from __future__ import annotations

import copy
import re

VERSION = 24
INTERIOR_CONTEXT_VERSION = 18
NEIGHBOR_POLICY_VERSION = 16


def proposal_transaction_matches(base_project, edited, pending, alignment):
    """A joint calibration cannot be committed with a different cut mask."""
    rows = {row["id"]: row for row in edited}
    base = {row["id"]: row for row in base_project["segments"]}
    changed = set(alignment.get("rows", []))
    held = []
    expected = {sid: set(base[sid].get("removed", [])) for sid in changed if sid in base}
    for cut in pending:
        if cut["id"] in expected:
            if alignment.get("verifiedCutMasksVersion") == 1:
                sid = cut["id"]
                spoken_indices = {i for i in cut["indices"] if any(c.isalnum() for c in base[sid]["words"][i]["word"])}
                if not spoken_indices.issubset(set(alignment.get("verifiedCutMasks", {}).get(sid, []))):
                    continue
            expected[cut["id"]].update(cut["indices"])
    for sid in changed:
        row = rows.get(sid)
        original = base.get(sid)
        if (
            row is None
            or original is None
            or row.get("deleted") != original.get("deleted")
            or [word["word"] for word in row["words"]] != [word["word"] for word in original["words"]]
        ):
            held.append({"id": sid, "reason": "校准后原话或整句状态变化"})
            continue
        spoken = {i for i, word in enumerate(row["words"]) if any(c.isalnum() for c in word["word"])}
        wanted = expected[sid] & spoken
        actual = set(row.get("removed", [])) & spoken
        if wanted != actual:
            held.append({"id": sid, "missing": sorted(wanted - actual), "extra": sorted(actual - wanted)})
    return {"passed": not held, "held": held, "version": 1}


def row_versions(record):
    revision = record.get("alignmentRevision", {})
    versions = dict(revision.get("rowVersions", {}))
    for sid in revision.get("rows", []):
        versions[sid] = max(versions.get(sid, 0), revision.get("version", 0))
    return versions


def aligned_chars(row, groups, second, third=None):
    if "".join(group["word"] for group in groups) != row["text"] or [group["word"] for group in groups] != [
        group["word"] for group in second
    ]:
        return None
    peers = [second]
    if third and [group["word"] for group in third] == [group["word"] for group in groups]:
        peers.append(third)
    out = []
    for index, (left, _right) in enumerate(zip(groups, second)):
        lo = max(row["start"], min(row["end"], left["start"]))
        hi = max(lo, min(row["end"], left["end"]))
        consensus = [
            peer[index]
            for peer in peers
            if abs(left["end"] - peer[index]["end"]) <= 0.08 and (index == 0 or abs(left["start"] - peer[index]["start"]) <= 0.08)
        ]
        stable = bool(consensus)
        for offset, char in enumerate(left["word"]):
            out.append(
                {
                    "word": char,
                    "start": lo + (hi - lo) * offset / len(left["word"]),
                    "end": lo + (hi - lo) * (offset + 1) / len(left["word"]),
                    "probability": left["probability"],
                    "timingEstimated": True,
                    "alignmentGroup": str(index),
                    "alignmentStable": stable,
                    "alignmentProbability": left["probability"],
                }
            )
    if [word["word"] for word in out] != [word["word"] for word in row["words"]]:
        return None
    return out


def interior_filler_context(source_row, edit):
    words = source_row["words"]
    removed = set(edit.get("removed", []))
    if edit.get("deleted") or not removed:
        return False
    if [word["word"] for word in words] != [word["word"] for word in edit["words"]]:
        return False
    if any(type(index) is not int or index < 0 or index >= len(words) for index in removed):
        return False

    def filler(word):
        return bool(re.fullmatch(r"[呃嗯啊额哦]+", word))

    if any(not filler(words[index]["word"]) for index in removed):
        return False
    spoken = [index for index, word in enumerate(words) if any(char.isalnum() for char in word["word"])]
    for position, index in enumerate(spoken):
        if index not in removed:
            continue
        if position and spoken[position - 1] in removed:
            continue
        last = position
        while last + 1 < len(spoken) and spoken[last + 1] in removed:
            last += 1
        left = spoken[max(0, position - 2) : position]
        right = spoken[last + 1 : last + 3]
        if len(left) != 2 or len(right) != 2:
            return False
        if any(item in removed or filler(words[item]["word"]) for item in left + right):
            return False
    return True


def required_row_version(row):
    return INTERIOR_CONTEXT_VERSION if interior_filler_context(row, row) else NEIGHBOR_POLICY_VERSION


def tighten_words(words: list[dict], samples, sample_rate: int = 16000) -> list[dict]:
    """Pull silence off the edges of a timed word. Does not invent new text."""
    from engine.acoustic import FRAME, frame_db, label_db

    levels = frame_db(samples, sample_rate)
    tightened = copy.deepcopy(words)

    def frame_at(second: float) -> int:
        return max(0, min(len(levels) - 1, int(second / FRAME)))

    for word in tightened:
        start = frame_at(word["start"])
        end = max(start + 1, frame_at(word["end"]))
        while start + 1 < end and label_db(levels[start]) == "silence":
            start += 1
        while end - 1 > start and label_db(levels[end - 1]) == "silence":
            end -= 1
        word["start"] = round(start * FRAME, 3)
        word["end"] = round(max(word["start"] + 0.04, end * FRAME), 3)
    return tightened
