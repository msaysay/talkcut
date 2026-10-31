"""Beat grid from a BPM, or from onsets in a user-supplied music file."""

from __future__ import annotations

import array
import math
import wave
from pathlib import Path


def beats_from_bpm(duration: float, bpm: float, offset: float = 0.0) -> list[float]:
    if bpm <= 0 or duration <= 0:
        return []
    period = 60.0 / bpm
    beats = []
    cursor = offset
    while cursor < duration - 0.02:
        beats.append(round(cursor, 3))
        cursor += period
    return beats


def detect_beats(samples: array.array, sample_rate: int = 16000, bpm_hint: float | None = None) -> tuple[list[float], float]:
    duration = len(samples) / sample_rate if sample_rate else 0
    if bpm_hint:
        return beats_from_bpm(duration, bpm_hint), float(bpm_hint)
    frame = max(1, int(sample_rate * 0.02))
    energies: list[float] = []
    for index in range(0, len(samples), frame):
        block = samples[index : index + frame]
        if not block:
            break
        energies.append(sum(value * value for value in block) / len(block))
    if len(energies) < 4:
        return beats_from_bpm(duration, 100), 100.0
    diffs = [0.0]
    for index in range(1, len(energies)):
        diffs.append(max(0.0, energies[index] - energies[index - 1]))
    ordered = sorted(diffs)
    threshold = ordered[int(len(ordered) * 0.86)]
    peaks: list[float] = []
    for index, delta in enumerate(diffs):
        if delta < threshold or delta <= 0:
            continue
        when = index * 0.02
        if peaks and when - peaks[-1] < 0.28:
            continue
        peaks.append(round(when, 3))
    if len(peaks) < 2:
        return beats_from_bpm(duration, 100), 100.0
    intervals = [right - left for left, right in zip(peaks, peaks[1:])]
    median = sorted(intervals)[len(intervals) // 2]
    bpm = round(60.0 / median, 1) if median > 0 else 100.0
    return peaks, bpm


def write_drum_bed(path: Path, duration: float, bpm: float = 96, sample_rate: int = 16000) -> list[float]:
    """A short kick pulse so a render has music before the user brings a track."""
    count = max(1, int(duration * sample_rate))
    samples = array.array("h", [0] * count)
    beats = beats_from_bpm(duration, bpm)
    pulse = int(0.045 * sample_rate)
    for beat in beats:
        start = int(beat * sample_rate)
        for index in range(pulse):
            at = start + index
            if at >= count:
                break
            envelope = 1 - index / pulse
            samples[at] = int(0.55 * 32767 * math.sin(2 * math.pi * 72 * index / sample_rate) * envelope)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(samples.tobytes())
    return beats
