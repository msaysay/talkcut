"""Locate ffmpeg and optional ASR without a host-specific install path."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from engine.errors import TalkCutError

REPO = Path(__file__).resolve().parents[1]
RUNTIME = REPO / "runtime"
CONFIG = RUNTIME / "config.json"


def _which(name: str, override: str | None) -> str | None:
    if override:
        path = Path(override).expanduser()
        return str(path.resolve()) if path.is_file() else None
    found = shutil.which(name)
    return found


def load_config() -> dict:
    if not CONFIG.is_file():
        return {}
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def ffmpeg_path(override: str | None = None) -> str | None:
    return override or load_config().get("ffmpeg") or _which("ffmpeg", None)


def ffprobe_path(override: str | None = None) -> str | None:
    return override or load_config().get("ffprobe") or _which("ffprobe", None)


def require_ffmpeg() -> tuple[str, str]:
    ffmpeg = ffmpeg_path()
    ffprobe = ffprobe_path()
    if not ffmpeg or not ffprobe:
        raise TalkCutError("找不到 ffmpeg 或 ffprobe。安装后重试，或运行 setup --ffmpeg/--ffprobe 指向可执行文件。")
    return ffmpeg, ffprobe


def asr_status() -> dict:
    try:
        import faster_whisper  # noqa: F401

        installed = True
    except ImportError:
        installed = False
    return {
        "package": "faster-whisper",
        "installed": installed,
        "default": "energy",
        "note": "能量分段不需要模型。faster-whisper 为可选，模型在首次 --asr whisper 时由该库下载。",
    }


def write_config(*, ffmpeg: str, ffprobe: str, whisper_model: str = "small") -> Path:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "python": sys.executable,
        "ffmpeg": ffmpeg,
        "ffprobe": ffprobe,
        "asr": "opt-in",
        "whisperModel": whisper_model,
        "apiKeysRequired": False,
    }
    CONFIG.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return CONFIG


def doctor_lines() -> tuple[list[str], int]:
    lines: list[str] = []
    code = 0
    ffmpeg, ffprobe = ffmpeg_path(), ffprobe_path()
    if ffmpeg and ffprobe:
        lines.append(f"ok  ffmpeg {ffmpeg}")
        lines.append(f"ok  ffprobe {ffprobe}")
    else:
        lines.append("缺  ffmpeg 或 ffprobe 不在 PATH，也没有 runtime/config.json")
        code = 1
    asr = asr_status()
    if asr["installed"]:
        lines.append("ok  faster-whisper 已安装（import --asr whisper 可用；模型另计）")
    else:
        lines.append("可选  faster-whisper 未安装。默认 import 使用能量分段，不下载语音模型。")
        lines.append("     需要转写时再运行 setup --with-asr，首次 whisper 会下载模型。")
    if CONFIG.is_file():
        lines.append(f"ok  runtime 配置 {CONFIG}")
    else:
        lines.append("注意  尚未写入 runtime/config.json。setup 会记下当前 ffmpeg，不创建宿主专用目录。")
    return lines, code
