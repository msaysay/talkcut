"""Energy labels for speech, breath, and silence.

Sayframe can suggest filler drafts, then refuse to delete the audio.
These labels are what TalkCut actually cuts.
"""

from __future__ import annotations

import math

SPEECH_DB = -25.0
BREATH_DB = -46.0
FRAME = 0.02


def frame_db(samples, sample_rate: int = 16000, frame: float = FRAME) -> list[float]:
    size = max(1, int(sample_rate * frame))
    levels = []
    for index in range(0, len(samples), size):
        block = samples[index : index + size]
        if not block:
            break
        mean_square = sum(value * value for value in block) / len(block)
        rms = math.sqrt(mean_square) / 32768
        levels.append(20 * math.log10(rms) if rms > 1e-8 else -90.0)
    return levels


def label_db(level: float) -> str:
    if level >= SPEECH_DB:
        return "speech"
    if level >= BREATH_DB:
        return "breath"
    return "silence"


def smooth(labels: list[str]) -> list[str]:
    if len(labels) < 3:
        return labels
    out = labels[:]
    for index in range(1, len(out) - 1):
        if out[index - 1] == out[index + 1] and out[index] != out[index - 1]:
            out[index] = out[index - 1]
    return out


def spans_from_pcm(samples, sample_rate: int = 16000) -> list[dict]:
    levels = frame_db(samples, sample_rate)
    labels = smooth([label_db(level) for level in levels])
    spans: list[dict] = []
    index = 0
    while index < len(labels):
        end = index + 1
        while end < len(labels) and labels[end] == labels[index]:
            end += 1
        spans.append(
            {
                "kind": labels[index],
                "start": round(index * FRAME, 3),
                "end": round(end * FRAME, 3),
            }
        )
        index = end
    duration = round(len(samples) / sample_rate, 3)
    if spans:
        spans[-1]["end"] = duration
    return _absorb(spans)


def _absorb(spans: list[dict]) -> list[dict]:
    """Fold sub-frame breaths and clicks into a neighbor so cuts stay on real gaps."""
    pending = [dict(span) for span in spans]
    changed = True
    while changed and pending:
        changed = False
        merged: list[dict] = []
        for span in pending:
            duration = span["end"] - span["start"]
            short_silence = span["kind"] == "silence" and duration < 0.08
            short_breath = span["kind"] == "breath" and duration < 0.12
            if merged and (short_silence or short_breath):
                merged[-1]["end"] = span["end"]
                changed = True
                continue
            if merged and merged[-1]["kind"] == span["kind"]:
                merged[-1]["end"] = span["end"]
                continue
            merged.append(dict(span))
        pending = merged
    return pending


def dominant_kind(samples, start: float, end: float, sample_rate: int = 16000) -> str:
    if end - start <= 0:
        return "silence"
    first = max(0, int(start * sample_rate))
    last = max(first + 1, int(end * sample_rate))
    window = samples[first:last]
    if not window:
        return "silence"
    levels = frame_db(window, sample_rate)
    if not levels:
        return "silence"
    counts = {"speech": 0, "breath": 0, "silence": 0}
    for level in levels:
        counts[label_db(level)] += 1
    return max(counts, key=counts.get)


def words_from_pcm(samples, sample_rate: int = 16000) -> list[dict]:
    words = []
    speech_index = 0
    for span in spans_from_pcm(samples, sample_rate):
        duration = span["end"] - span["start"]
        if duration < 0.04:
            continue
        kind = span["kind"]
        if kind == "speech":
            speech_index += 1
            text = f"口播{speech_index}"
        elif kind == "breath":
            text = "〔气口〕"
        else:
            text = "〔静音〕"
        words.append(
            {
                "word": text,
                "start": span["start"],
                "end": span["end"],
                "kind": kind,
            }
        )
    return words
