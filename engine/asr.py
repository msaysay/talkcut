"""Optional faster-whisper transcription.

The model download stays opt-in. Import uses energy segmentation until this
package is installed and the caller passes --asr whisper.
"""

from __future__ import annotations

from pathlib import Path

from engine.errors import TalkCutError


def available() -> bool:
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        return False
    return True


def transcribe(path: Path, model_size: str = "small") -> list[dict]:
    if not available():
        raise TalkCutError(
            "faster-whisper 未安装。先运行 setup --with-asr，或改用默认的 --asr energy。"
            "模型在第一次转写时下载，不在 doctor 里下载。"
        )
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _info = model.transcribe(str(path), language="zh", word_timestamps=True, vad_filter=True)
    words: list[dict] = []
    for segment in segments:
        timed = list(segment.words or [])
        if timed:
            for token in timed:
                text = (token.word or "").strip()
                if not text:
                    continue
                words.append({"word": text, "start": float(token.start), "end": float(token.end), "kind": "speech"})
            continue
        text = (segment.text or "").strip()
        if text:
            words.append({"word": text, "start": float(segment.start), "end": float(segment.end), "kind": "speech"})
    if not words:
        raise TalkCutError("faster-whisper 没有返回词。检查音轨，或改用 --asr energy。")
    return words
