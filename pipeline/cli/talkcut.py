#!/usr/bin/env python3
"""TalkCut pipeline CLI stub.

``doctor`` checks that the scaffold files are present.
``setup`` and the edit subcommands are reserved names; they are not implemented.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

METHODOLOGY = [
    "methodology/README.md",
    "methodology/01-business-ip-system.md",
    "methodology/02-content-conversion.md",
    "methodology/03-edit-directives.md",
    "methodology/04-naming-glossary.md",
    "methodology/EDIT_PIPELINE_HOOKS.json",
]

SCAFFOLD_FILES = METHODOLOGY + [
    "pipeline/contracts/planning-contract.json",
    "pipeline/contracts/edit-contract.json",
    "pipeline/stages/01_parse_and_plan.md",
    "pipeline/stages/02_rough_cut.md",
    "pipeline/stages/03_motion_music.md",
    "pipeline/stages/04_finish.md",
    "skills/talkcut/SKILL.md",
    "motion-pack/package.json",
    "motion-pack/src/Root.tsx",
    "engine/README.md",
]

IMPLEMENTED = {"doctor"}

RESERVED = {
    "setup": "安装 ffmpeg、本地 ASR 与工程运行时。尚未实现。",
    "import": "登记一条本地口播原片。尚未实现。",
    "read": "读出带原句 id 的转写。尚未实现。",
    "propose": "按方法论给出剪辑方向。确认前不导出。尚未实现。",
    "choose-plan": "把用户选定的方向写入工程。尚未实现。",
    "apply": "按 edit contract 做粗剪。尚未实现。",
    "motion": "套用 motion-pack 预设。尚未实现。",
    "cover": "生成封面与标题建议。尚未实现。",
    "export": "渲染成片。用户确认方向之前禁止调用。尚未实现。",
}


def doctor() -> int:
    print("TalkCut doctor（骨架）")
    missing = [rel for rel in SCAFFOLD_FILES if not (ROOT / rel).is_file()]
    if missing:
        print("缺文件：")
        for rel in missing:
            print(f"  - {rel}")
        return 1
    print(f"ok  骨架文件齐全（{len(SCAFFOLD_FILES)} 项）")
    print("注意  engine/ 仍是占位，sayframe 模块尚未移植")
    print("注意  setup 尚未实现（ffmpeg / ASR 运行时）")
    motion_modules = ROOT / "motion-pack" / "node_modules"
    if motion_modules.is_dir():
        print("ok  motion-pack 依赖已安装")
    else:
        print("注意  motion-pack 依赖未安装：在 motion-pack/ 执行 npm install")
    print("通过只表示骨架文件都在，不表示可以出片。")
    return 0


def reserved(name: str) -> int:
    print(f"TalkCut {name}：{RESERVED[name]}", file=sys.stderr)
    print("见 pipeline/README.md 与 docs/ROADMAP.md。", file=sys.stderr)
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="talkcut",
        description="TalkCut 流水线 CLI 骨架。目前只有 doctor 会检查文件。",
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("doctor", help="检查骨架文件是否齐全")
    for name, help_text in RESERVED.items():
        sub.add_parser(name, help=help_text)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help"}:
        build_parser().print_help()
        return 0
    command = args[0]
    if command in IMPLEMENTED:
        return doctor()
    if command in RESERVED:
        return reserved(command)
    print(f"未知命令 {command}", file=sys.stderr)
    build_parser().print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
