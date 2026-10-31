#!/usr/bin/env python3
"""Download one commercially usable music bed. The file is not committed.

Music stays off unless you pass --music. This script is the second way in:
fetch a track you are allowed to use, then point --music at it. TalkCut does
not synthesize a metronome or drum bed.
"""

from __future__ import annotations

import argparse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_URL = "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Local%20Forecast.mp3"
DEFAULT_OUT = ROOT / "runtime" / "music" / "local-forecast.mp3"
CREDIT = "Kevin MacLeod (incompetech.com) — Local Forecast, CC BY 4.0, https://creativecommons.org/licenses/by/4.0/"


def main() -> int:
    parser = argparse.ArgumentParser(description="下载一条可商用配乐到 runtime/music，不写入 git。")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()
    dest = Path(args.out).expanduser().resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 100_000:
        print(f"已存在 {dest}")
    else:
        print(f"下载 {args.url}")
        urllib.request.urlretrieve(args.url, dest)
    print(f"文件 {dest}")
    print(f"署名 {CREDIT}")
    print("仓库不提交这个音频。渲染时显式传入，例如：")
    print(f'python3 pipeline/cli/talkcut.py motion --project <工程> --preset opus-clean --music "{dest}"')
    print("不传 --music 时成片没有配乐。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
