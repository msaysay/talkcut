"""Plan breath, filler, and silence removals, then let export cut the audio.

Upstream left word deletion as a draft and export rejected it. The removals
returned here are executed by engine.cuts.
"""

from __future__ import annotations

import re

from engine.shared.disfluency_grammar import hold_reason

FILLER = re.compile(r"^(?:呃|嗯|啊|额|哦|唔|um|uh|hmm|嗯嗯|啊啊)+$", re.IGNORECASE)
MARKER = {"〔气口〕": "breath", "〔静音〕": "silence"}


def word_reason(word: dict) -> str | None:
    text = str(word.get("word", "")).strip()
    if text in MARKER:
        return MARKER[text]
    if FILLER.fullmatch(text):
        return "filler"
    kind = word.get("kind")
    if kind in {"breath", "silence", "filler"}:
        return kind
    return None


def plan_removals(segments: list[dict], cleanup: dict, keep_ids: set[str]) -> list[dict]:
    """Return removeWords entries. Kept human-moment segments skip automatic cuts."""
    flags = {
        "breath": bool(cleanup.get("breath")),
        "filler": bool(cleanup.get("filler")),
        "silence": bool(cleanup.get("silence")),
    }
    planned = []
    for segment in segments:
        if segment["id"] in keep_ids or segment.get("deleted"):
            continue
        grouped: dict[str, list[int]] = {}
        for index, word in enumerate(segment["words"]):
            reason = word_reason(word)
            if reason is None or not flags.get(reason):
                continue
            if reason == "filler" and hold_reason(segment, [index], segments):
                continue
            grouped.setdefault(reason, []).append(index)
        for reason, indices in grouped.items():
            # Split into contiguous runs so a quote matches the words.
            run: list[int] = []
            for index in indices:
                if run and index != run[-1] + 1:
                    planned.append(_entry(segment, run, reason))
                    run = []
                run.append(index)
            if run:
                planned.append(_entry(segment, run, reason))
    return planned


def _entry(segment: dict, indices: list[int], reason: str) -> dict:
    quote = "".join(segment["words"][index]["word"] for index in indices)
    return {
        "id": segment["id"],
        "indices": indices,
        "quote": quote,
        "reason": reason,
        "automatic": True,
    }
