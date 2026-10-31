"""Project JSON on disk. The source media stays where the user put it."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from engine.errors import TalkCutError

FILENAME = "project.json"


def project_path(folder: Path) -> Path:
    return folder / FILENAME


def load(folder: Path) -> dict:
    path = project_path(folder)
    if not path.is_file():
        raise TalkCutError(f"找不到工程：{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def save(folder: Path, project: dict) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    path = project_path(folder)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def revision_of(project: dict) -> str:
    payload = {
        "source": project["source"]["sha256"],
        "segments": [
            {
                "id": segment["id"],
                "words": [
                    {"word": word["word"], "start": word["start"], "end": word["end"]}
                    for word in segment["words"]
                ],
            }
            for segment in project["segments"]
        ],
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()
