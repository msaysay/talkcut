"""Download OFL fonts into runtime/fonts. Binaries stay out of git."""

from __future__ import annotations

import json
import shutil
import urllib.request
import zipfile
from pathlib import Path

from engine.errors import TalkCutError

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "motion-pack" / "fonts" / "manifest.json"
FONT_DIR = REPO / "runtime" / "fonts"


def manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def ensure_fonts() -> dict[str, Path]:
    payload = manifest()
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    for item in payload["downloads"]:
        target = FONT_DIR / item["file"]
        unzip_name = item.get("unzip")
        ready = FONT_DIR / unzip_name if unzip_name else target
        if ready.is_file() and ready.stat().st_size > 1000:
            continue
        _download(item["url"], target)
        if unzip_name:
            with zipfile.ZipFile(target) as bundle:
                member = next(name for name in bundle.namelist() if name.endswith(unzip_name))
                with bundle.open(member) as source, (FONT_DIR / unzip_name).open("wb") as dest:
                    shutil.copyfileobj(source, dest)
    found = {}
    missing = []
    for role, spec in payload["roles"].items():
        path = FONT_DIR / spec["file"]
        if path.is_file():
            found[role] = path
        else:
            missing.append(role)
    if not found.get("fallback") and not found.get("body"):
        raise TalkCutError("字体没有下载成功。检查网络后重试 setup --fonts。")
    if missing:
        print("可选字体缺失，渲染时回退到 Noto Sans SC 或已有的正文字体：" + ", ".join(missing))
    return found


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "TalkCut/0.1"})
    with urllib.request.urlopen(request, timeout=120) as response, dest.open("wb") as handle:
        shutil.copyfileobj(response, handle)
