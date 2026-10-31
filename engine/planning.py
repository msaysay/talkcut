"""One rough-cut direction from the methodology hooks.

This is not a semantic model. It names the video type, the first spoken span,
and the breath/silence/filler words already labeled on the transcript.
"""

from __future__ import annotations

import json
from pathlib import Path

from engine.errors import TalkCutError
from engine.shared.speech_cleanup import word_reason

HOOKS = Path(__file__).resolve().parents[1] / "methodology" / "EDIT_PIPELINE_HOOKS.json"


def load_hooks() -> dict:
    return json.loads(HOOKS.read_text(encoding="utf-8"))


def propose(project: dict) -> dict:
    hooks = load_hooks()
    catalog = hooks.get("meta", {}).get("version", "0")
    speech = []
    cuts = []
    for segment in project["segments"]:
        spoken = [word for word in segment["words"] if word_reason(word) is None]
        if spoken:
            speech.append(segment)
        for index, word in enumerate(segment["words"]):
            reason = word_reason(word)
            if reason in {"breath", "silence", "filler"}:
                cuts.append(
                    {
                        "id": segment["id"],
                        "indices": [index],
                        "text": word["word"],
                        "reason": reason,
                        "start": word["start"],
                        "end": word["end"],
                    }
                )
    if not project["segments"]:
        raise TalkCutError("没有可规划的片段。")
    hook_segment = speech[0] if speech else project["segments"][0]
    hook_word = next((word for word in hook_segment["words"] if word_reason(word) is None), hook_segment["words"][0])
    order = [segment["id"] for segment in project["segments"]]
    direction = {
        "id": "rough-cleanup",
        "title": "去掉气口、长静音和单独填充词",
        "video_type": "pillar_daily",
        "journey_role": "why_me",
        "audience": "未从口播里判断具体付费人群",
        "goal": "保留说出来的句子，切掉气口、长静音和单独的填充词",
        "hook_candidate": {
            "text": hook_word["word"],
            "segmentIds": [hook_segment["id"]],
            "start": hook_word["start"],
            "end": hook_word["end"],
        },
        "opening_style": "笃定式",
        "order": order,
        "cut_candidates": cuts,
        "why": "方法论要求前 3 秒有钩子，并删掉钩子前的无效准备和过长沉默。这一步只根据声学和填充词，不改写原话。",
        "gaps": [] if project.get("asr") == "faster-whisper" else ["能量分段没有语义文稿。确认方向前可以用 --asr whisper 或 --transcript。"],
    }
    return {
        "format": "talkcut-planning-v0",
        "catalogVersion": catalog,
        "sourceSha256": project["source"]["sha256"],
        "revision": project["revision"],
        "directions": [direction],
        "notice": "这是轻量建议，不是成片。确认前不要导出。",
    }
