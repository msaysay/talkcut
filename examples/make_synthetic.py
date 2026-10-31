#!/usr/bin/env python3
"""Write a synthetic talking-head stand-in and print the import/apply/export commands.

No sample footage is committed. The picture is a flat color; the soundtrack is
tones, one breath, and silence.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.runtime import require_ffmpeg
from engine.synthetic import make_breath_demo, make_filler_demo


def main() -> int:
    parser = argparse.ArgumentParser(description="生成可本地跑通的合成口播。")
    parser.add_argument("--out", default="examples/out", help="输出目录，默认 examples/out")
    args = parser.parse_args()
    ffmpeg, _ffprobe = require_ffmpeg()
    folder = Path(args.out).expanduser().resolve()
    breath = make_breath_demo(folder, ffmpeg)
    filler = make_filler_demo(folder, ffmpeg)
    print("合成原片已写好。画面是纯色，声音是蜂鸣、气口和静音。")
    print(f"气口样例  {breath['video']}")
    print(f"填充词样例 {filler['video']}")
    print()
    print("气口样例可以叠合成中文字幕。文稿时间对齐蜂鸣，不下载语音模型：")
    print(
        f"  python3 pipeline/cli/talkcut.py import --video {breath['video']} "
        f"--project {folder}/breath-project --transcript examples/demo-caption-words.json"
    )
    print(f"  python3 pipeline/cli/talkcut.py read --project {folder}/breath-project")
    print("  # changes.json：revision 用 read 的值，confirmed 为 true，cleanup 打开 breath/silence")
    print(f"  python3 pipeline/cli/talkcut.py apply --project {folder}/breath-project --changes changes.json")
    print(f"  python3 pipeline/cli/talkcut.py motion --project {folder}/breath-project --preset clean-knowledge")
    print(f"  python3 pipeline/cli/talkcut.py motion --project {folder}/breath-project --preset gold-line --music <你的BGM>")
    print(f"  python3 pipeline/cli/talkcut.py export --project {folder}/breath-project")
    print()
    print("逐词去掉「嗯」（文稿时间，响度仍然很大）：")
    print(
        f"  python3 pipeline/cli/talkcut.py import --video {filler['video']} "
        f"--project {folder}/filler-project --transcript {filler['transcript']}"
    )
    print("  # removeWords 指向该词的 indices，或 cleanup.filler = true")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 — example script prints the reason and stops
        print(exc, file=sys.stderr)
        raise SystemExit(2) from exc
