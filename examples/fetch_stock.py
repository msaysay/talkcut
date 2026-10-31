#!/usr/bin/env python3
"""Download a commercially usable talking-head clip. The file is not committed.

Default source is a Pexels video (Pexels license: free to use, including
commercially, no attribution required). We still record the page in
THIRD_PARTY_NOTICES.md. Pass --url to use another direct file URL.
"""

from __future__ import annotations

import argparse
import urllib.request
from pathlib import Path

DEFAULT_URL = "https://videos.pexels.com/video-files/8048443/8048443-hd_1080_1920_25fps.mp4"
DEFAULT_PAGE = "https://www.pexels.com/video/woman-talking-in-front-of-the-camera-8048443/"


def main() -> int:
    parser = argparse.ArgumentParser(description="下载可商用的公开口播视频，不写入 git。")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--out", default="examples/out/pexels-talking-head.mp4")
    args = parser.parse_args()
    dest = Path(args.out).expanduser().resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 100_000:
        print(f"已存在 {dest}")
    else:
        print(f"下载 {args.url}")
        urllib.request.urlretrieve(args.url, dest)
    print(f"文件 {dest}")
    print(f"来源页面 {DEFAULT_PAGE}")
    print("许可：Pexels License，可商用，不要求署名。仓库不提交这个 mp4。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
