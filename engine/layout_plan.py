"""Assign a layout, caption role, and beat to each spoken line.

Rules live in methodology/layout-rules.json. The default classifier is local
keywords and position. `--classify agent` only writes a prompt for the host
model; this process does not call a language API.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from engine.beats import beats_from_bpm
from engine.errors import TalkCutError

RULES_PATH = Path(__file__).resolve().parents[1] / "methodology" / "layout-rules.json"


def load_rules(path: Path | None = None) -> dict:
    source = path or RULES_PATH
    if not source.is_file():
        raise TalkCutError(f"找不到版式规则：{source}")
    return json.loads(source.read_text(encoding="utf-8"))


def load_script(path: Path) -> list[dict]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = payload.get("sentences") if isinstance(payload, dict) else payload
    if not isinstance(rows, list) or not rows:
        raise TalkCutError("文稿需要 sentences 数组。")
    sentences = []
    for index, row in enumerate(rows, start=1):
        text = str(row.get("text") or "").strip()
        start, end = float(row["start"]), float(row["end"])
        if not text or end <= start:
            raise TalkCutError(f"第 {index} 句文本或时间无效。")
        sentences.append(
            {
                "id": str(row.get("id") or f"s{index}"),
                "text": text,
                "start": round(start, 3),
                "end": round(end, 3),
                "role": row.get("role"),
            }
        )
    return sentences


def classify_sentence(sentence: dict, rules: dict, index: int) -> tuple[str, str]:
    if sentence.get("role") in rules["roles"]:
        return sentence["role"], "句子里已经写了角色"
    spec = rules["classify"]
    if index == 0 and sentence["start"] < float(spec.get("hookMaxStart", 3)):
        return "hook", "前 3 秒的第一句，当作钩子"
    patterns = spec.get("patterns") or {}
    for role in spec.get("priority") or []:
        for pattern in patterns.get(role) or []:
            if re.search(pattern, sentence["text"]):
                return role, f"命中{rules['labels'].get(role, role)}特征"
    if "？" in sentence["text"] or sentence["text"].endswith("吗"):
        return "opinion", "问句，归到观点"
    if len(sentence["text"]) <= 8:
        return "bridge", "句子很短，当作过渡"
    return spec.get("default", "opinion"), "没有更强特征，默认观点"


def _layout_pair(role: str, orientation: str, rules: dict) -> tuple[str, str]:
    spec = rules["layouts"][role]
    if orientation == "landscape":
        return spec["landscape"], spec.get("landscapeAlternate") or spec["landscape"]
    return spec["vertical"], spec.get("verticalAlternate") or spec["vertical"]


def _family(layout: str, rules: dict) -> str:
    for name, members in (rules.get("families") or {}).items():
        if layout in members:
            return name
    return "graphic"


def _keywords(text: str) -> list[str]:
    found = []
    for match in re.finditer(r"\d+|[零〇一二三四五六七八九十]+", text):
        token = match.group(0)
        if token not in found:
            found.append(token)
    for token in ("痛点", "最痛", "真正", "金句", "比如", "钩子"):
        if token in text and token not in found:
            found.append(token)
    return found


def apply_rhythm(items: list[dict], rules: dict, orientation: str, beats: list[float]) -> list[dict]:
    rhythm = rules["rhythm"]
    minimum = float(rhythm["minLayoutSeconds"])
    max_count = int(rhythm["maxSameLayoutSentences"])
    max_seconds = float(rhythm["maxSameLayoutSeconds"])
    max_gold = int(rhythm["maxGold"])
    snap_tol = float(rhythm.get("beatSnapSeconds", 0.22))
    golds = [item for item in items if item["role"] == "gold"]
    if len(golds) > max_gold:
        keep = max(golds, key=lambda item: item["end"] - item["start"])
        for item in golds:
            if item is keep:
                continue
            item["role"] = "opinion"
            item["reasons"].append("金句数量已满，这一句改作观点")
    merged: list[dict] = []
    for item in items:
        duration = item["end"] - item["start"]
        if merged and duration < minimum:
            merged[-1]["end"] = item["end"]
            merged[-1]["text"] += item["text"]
            merged[-1]["reasons"].append(f"不足 {minimum:.1f} 秒，并入上一句")
            continue
        merged.append(item)
    if len(merged) > 1 and merged[0]["end"] - merged[0]["start"] < minimum:
        merged[1]["start"] = merged[0]["start"]
        merged[1]["text"] = merged[0]["text"] + merged[1]["text"]
        merged[1]["reasons"].append("首句太短，并入下一句")
        merged = merged[1:]
    run_layout = None
    run_count = 0
    run_start = 0.0
    previous_family = None
    for item in merged:
        spec = rules["layouts"][item["role"]]
        preferred, alternate = _layout_pair(item["role"], orientation, rules)
        layout = preferred
        if previous_family and rhythm.get("alternateFaceAndGraphic") and _family(layout, rules) == previous_family:
            if _family(alternate, rules) != previous_family:
                item["reasons"].append(f"上一句已是{_family_label(previous_family)}，改用备选 {alternate}")
                layout = alternate
        if layout == run_layout and (run_count + 1 > max_count or item["end"] - run_start > max_seconds):
            item["reasons"].append(f"同一版式已连续 {run_count} 句，改用备选 {alternate}")
            layout = alternate if alternate != layout else preferred
        if layout != run_layout:
            run_layout = layout
            run_count = 1
            run_start = item["start"]
        else:
            run_count += 1
        item["layout"] = layout
        item["family"] = _family(layout, rules)
        item["roleLabel"] = rules["labels"].get(item["role"], item["role"])
        item["emphasis"] = spec["emphasis"]
        item["font"] = spec["font"]
        item["effects"] = list(spec.get("effects") or [])
        previous_family = item["family"]
    _snap_beats(merged, beats, minimum, snap_tol)
    return merged


def _family_label(name: str) -> str:
    return "人脸全屏" if name == "face" else "图文版式"


def _snap_beats(items: list[dict], beats: list[float], minimum: float, tolerance: float) -> None:
    if not beats:
        return
    for index in range(len(items) - 1):
        boundary = items[index]["end"]
        nearest = min(beats, key=lambda beat: abs(beat - boundary))
        if abs(nearest - boundary) > tolerance:
            items[index + 1]["transitionBeat"] = None
            continue
        if nearest - items[index]["start"] < minimum - 0.05:
            continue
        if items[index + 1]["end"] - nearest < minimum - 0.05:
            continue
        items[index]["end"] = round(nearest, 3)
        items[index + 1]["start"] = round(nearest, 3)
        items[index + 1]["transitionBeat"] = round(nearest, 3)
        items[index]["reasons"].append(f"切到下一句时对齐鼓点 {nearest:.2f} 秒")


def build_plan(
    sentences: list[dict],
    orientation: str,
    rules: dict | None = None,
    *,
    beats: list[float] | None = None,
    bpm: float = 96,
    video: str | None = None,
    classify: str = "rules",
) -> dict:
    if orientation not in {"vertical", "landscape"}:
        raise TalkCutError("--orientation 只能是 vertical 或 landscape。")
    rules = rules or load_rules()
    if not sentences:
        raise TalkCutError("没有可规划的句子。")
    duration = max(row["end"] for row in sentences)
    beat_grid = beats if beats is not None else beats_from_bpm(duration, bpm)
    items = []
    for index, sentence in enumerate(sentences):
        role, reason = classify_sentence(sentence, rules, index)
        items.append(
            {
                "id": sentence["id"],
                "text": sentence["text"],
                "start": sentence["start"],
                "end": sentence["end"],
                "role": role,
                "roleLabel": rules["labels"].get(role, role),
                "keywords": _keywords(sentence["text"]),
                "reasons": [reason],
                "transitionBeat": None,
            }
        )
    items = apply_rhythm(items, rules, orientation, beat_grid)
    for item in items:
        item["reason"] = "；".join(item["reasons"])
    return {
        "version": 1,
        "orientation": orientation,
        "classify": classify,
        "video": video,
        "duration": round(duration, 3),
        "bpm": bpm,
        "beats": beat_grid,
        "items": items,
    }


def render_table(plan: dict) -> str:
    lines = [
        f"# 版式计划（{ '竖屏' if plan['orientation'] == 'vertical' else '横屏' }）",
        "",
        "| 句子 | 角色 | 版式 | 字体 | 动效 | 理由 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in plan["items"]:
        effects = "、".join(item.get("effects") or []) or "—"
        lines.append(
            f"| {item['text']} | {item['roleLabel']} | {item['layout']} | {item['font']} | {effects} | {item['reason']} |"
        )
    return "\n".join(lines) + "\n"


def write_plan(folder: Path, plan: dict) -> tuple[Path, Path]:
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / "layout-plan.json"
    sided = folder / f"layout-plan-{plan['orientation']}.json"
    text = json.dumps(plan, ensure_ascii=False, indent=2) + "\n"
    target.write_text(text, encoding="utf-8")
    sided.write_text(text, encoding="utf-8")
    table = folder / "layout-plan.md"
    table.write_text(render_table(plan), encoding="utf-8")
    return target, table


def write_agent_request(folder: Path, sentences: list[dict], rules: dict | None = None) -> dict:
    rules = rules or load_rules()
    folder.mkdir(parents=True, exist_ok=True)
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["sentences"],
        "properties": {
            "sentences": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "role"],
                    "properties": {
                        "id": {"type": "string"},
                        "role": {"type": "string", "enum": rules["roles"]},
                    },
                },
            }
        },
    }
    catalog = "\n".join(f"- `{key}`：{label}" for key, label in rules["labels"].items())
    lines = "\n".join(f"- {row['id']} [{row['start']:.2f}-{row['end']:.2f}] {row['text']}" for row in sentences)
    prompt = (
        "你是口播剪辑助手。只给每句选一个角色，不要改写原句，不要安排版式，不要调用任何模型 API。\n"
        "TalkCut 会根据 methodology/layout-rules.json 把角色变成版式。\n\n"
        f"允许的 role：\n{catalog}\n\n"
        "前 3 秒的第一句通常是钩子。有数字、案例、步骤、金句、行动号召的句子用对应角色。不确定就用 opinion。\n"
        "把结果写成 JSON，字段只有 sentences[].id 和 sentences[].role。\n\n"
        f"句子：\n{lines}\n"
    )
    (folder / "classify-schema.json").write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (folder / "classify-prompt.md").write_text(prompt, encoding="utf-8")
    (folder / "classify-input.json").write_text(
        json.dumps({"sentences": sentences}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "status": "waiting-for-host",
        "prompt": str(folder / "classify-prompt.md"),
        "schema": str(folder / "classify-schema.json"),
        "input": str(folder / "classify-input.json"),
        "next": "宿主模型按 schema 写入 classify-result.json 后，再运行 plan --classify agent --roles classify-result.json",
    }


def apply_agent_roles(sentences: list[dict], roles_path: Path, rules: dict) -> list[dict]:
    payload = json.loads(Path(roles_path).read_text(encoding="utf-8"))
    rows = payload.get("sentences") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise TalkCutError("角色文件需要 sentences 数组。")
    by_id = {str(row.get("id")): row.get("role") for row in rows}
    updated = []
    for sentence in sentences:
        role = by_id.get(sentence["id"])
        if role not in rules["roles"]:
            raise TalkCutError(f"{sentence['id']} 的角色无效：{role}")
        updated.append({**sentence, "role": role})
    return updated


def sentences_from_project(project: dict) -> list[dict]:
    from engine.motion import captions_from_edit

    rows = captions_from_edit(project, "clean-knowledge")
    return [
        {"id": f"s{index}", "text": row["text"], "start": row["start"], "end": row["end"], "role": None}
        for index, row in enumerate(rows, start=1)
    ]
