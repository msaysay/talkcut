"""Host-agnostic audio preparation and transcript receipts.

The timestamp line format matches sayframe's native receipt so a host can hand
back timed text. TalkCut does not look up a host install directory or account.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

from engine.errors import TalkCutError
from engine.media import run

ACCEPTED_TOOLS = {"AudioTranscribe", "talkcut.transcript"}


def digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def seconds(clock: str) -> float:
    parts = [float(piece) for piece in clock.split(":")]
    if len(parts) not in (2, 3) or any(value < 0 for value in parts) or any(value >= 60 for value in parts[1:]):
        raise TalkCutError("转写时间格式无效。")
    return sum(value * 60**index for index, value in enumerate(reversed(parts)))


def prepare(video: Path, directory: Path, ffmpeg: str, duration: float) -> dict:
    source = video.expanduser().resolve()
    out = directory.expanduser().resolve()
    if not source.is_file():
        raise TalkCutError("原视频不存在。")
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise TalkCutError("音轨准备目录须为空。")
    source_sha = digest_file(source)
    parts = []
    for index, start in enumerate(range(0, math.ceil(duration), 1800)):
        end = min(duration, start + 1800)
        file = out / f"audio-{index + 1:03}.m4a"
        run(
            [
                ffmpeg,
                "-n",
                "-v",
                "error",
                "-ss",
                str(start),
                "-i",
                str(source),
                "-t",
                str(end - start),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "aac",
                "-b:a",
                "64k",
                str(file),
            ]
        )
        parts.append(
            {
                "id": f"a{index + 1}",
                "file": str(file),
                "sha256": digest_file(file),
                "sourceStart": start,
                "sourceEnd": end,
            }
        )
    if digest_file(source) != source_sha:
        raise TalkCutError("音轨准备期间原视频变化，停止。")
    manifest = {
        "version": 1,
        "video": str(source),
        "sourceSha256": source_sha,
        "duration": duration,
        "parts": parts,
        "next": "由宿主对每个 part 回传带时间的原文；TalkCut 不绑定特定宿主工具名。",
    }
    (out / "prepared-audio.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def validate(manifest: dict, receipt: dict) -> list[dict]:
    if receipt.get("tool") not in ACCEPTED_TOOLS or receipt.get("sourceSha256") != manifest["sourceSha256"]:
        raise TalkCutError("转写回执与音轨清单不匹配。")
    if digest_file(Path(manifest["video"])) != manifest["sourceSha256"]:
        raise TalkCutError("原视频变化，拒绝这份转写。")
    expected = {part["id"]: part for part in manifest["parts"]}
    seen: set[str] = set()
    rows = []
    for result in receipt.get("parts", []):
        part = expected.get(result.get("id"))
        if (
            not part
            or part["id"] in seen
            or result.get("audioSha256") != part["sha256"]
            or digest_file(Path(part["file"])) != part["sha256"]
        ):
            raise TalkCutError("音轨回执缺失、重复或来源不符。")
        raw = result.get("rawResult")
        if not isinstance(raw, str) or not raw.strip():
            raise TalkCutError("转写回执需要原始时间行，不能只交摘要。")
        matched = 0
        for line in raw.splitlines():
            match = re.fullmatch(r"\s*\[([\d:.]+)\s*,\s*([\d:.]+)\s*,\s*([^\]]+)\]\s*(\S.*?)\s*", line)
            if not match:
                continue
            start, end = seconds(match[1]), seconds(match[2])
            limit = part["sourceEnd"] - part["sourceStart"]
            if not 0 <= start < end <= limit + 0.3:
                raise TalkCutError("转写时间超出对应音轨。")
            rows.append(
                {
                    "start": part["sourceStart"] + start,
                    "end": min(part["sourceEnd"], part["sourceStart"] + end),
                    "speakerLabel": match[3],
                    "text": match[4],
                    "part": part["id"],
                }
            )
            matched += 1
        if not matched:
            raise TalkCutError("没有解析到时间行。")
        seen.add(part["id"])
    if seen != set(expected):
        raise TalkCutError("还有音轨没有转写。")
    rows.sort(key=lambda row: row["start"])
    return rows
