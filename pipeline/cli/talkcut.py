#!/usr/bin/env python3
"""TalkCut pipeline CLI.

doctor/setup discover local tools. import/apply/export run the edit engine.
ASR model download is opt-in via setup --with-asr and import --asr whisper.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.errors import TalkCutError
from engine.pipeline import (
    apply_edit,
    choose_plan,
    cover_frame,
    export_movie,
    import_media,
    motion_hook,
    propose,
    read_project,
)
from engine.runtime import asr_status, doctor_lines, ffmpeg_path, ffprobe_path, write_config

SCAFFOLD_FILES = [
    "methodology/README.md",
    "methodology/01-business-ip-system.md",
    "methodology/02-content-conversion.md",
    "methodology/03-edit-directives.md",
    "methodology/04-naming-glossary.md",
    "methodology/EDIT_PIPELINE_HOOKS.json",
    "pipeline/contracts/planning-contract.json",
    "pipeline/contracts/edit-contract.json",
    "skills/talkcut/SKILL.md",
    "engine/pipeline.py",
    "engine/shared/audio_cuts.py",
    "engine/shared/speech_alignment.py",
    "engine/shared/speech_cleanup.py",
    "engine/shared/smart_pauses.py",
    "engine/shared/editor_export.py",
    "engine/shared/video_finish.py",
    "engine/asr.py",
    "THIRD_PARTY_NOTICES.md",
]


def _print(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def command_doctor(_args: argparse.Namespace) -> int:
    print("TalkCut doctor")
    missing = [rel for rel in SCAFFOLD_FILES if not (ROOT / rel).is_file()]
    if missing:
        print("缺文件：")
        for rel in missing:
            print(f"  - {rel}")
        return 1
    print(f"ok  骨架与引擎文件（{len(SCAFFOLD_FILES)} 项）")
    lines, code = doctor_lines()
    for line in lines:
        print(line)
    motion = ROOT / "motion-pack" / "node_modules"
    if motion.is_dir():
        print("ok  motion-pack 依赖已安装（本轮导出不使用它）")
    else:
        print("可选  motion-pack 依赖未安装。粗剪导出不需要 Remotion。")
    if code == 0:
        print("ffmpeg 可用。语音模型未安装时，import 默认走能量分段。")
    return code


def command_setup(args: argparse.Namespace) -> int:
    ffmpeg = args.ffmpeg or ffmpeg_path()
    ffprobe = args.ffprobe or ffprobe_path()
    if not ffmpeg or not ffprobe:
        raise TalkCutError("找不到 ffmpeg 或 ffprobe。可以用 --ffmpeg 和 --ffprobe 传入路径。")
    config = write_config(ffmpeg=ffmpeg, ffprobe=ffprobe, whisper_model=args.whisper_model)
    print(f"已写入 {config}")
    print(f"ffmpeg  {ffmpeg}")
    print(f"ffprobe {ffprobe}")
    status = asr_status()
    if args.with_asr:
        if status["installed"]:
            print("faster-whisper 已在当前 Python 里。")
        else:
            print("正在安装 faster-whisper。模型要等第一次 import --asr whisper 才下载。")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "faster-whisper==1.2.1"],
                check=True,
            )
            print("faster-whisper 已安装。")
    elif status["installed"]:
        print("faster-whisper 已安装。")
    else:
        print("未安装 faster-whisper。默认 --asr energy，不下载模型。需要转写时再 setup --with-asr。")
    return 0


def command_import(args: argparse.Namespace) -> int:
    payload = import_media(
        Path(args.video),
        Path(args.project),
        transcript=Path(args.transcript) if args.transcript else None,
        asr=args.asr,
        whisper_model=args.whisper_model,
    )
    _print(payload)
    return 0


def command_read(args: argparse.Namespace) -> int:
    _print(read_project(Path(args.project)))
    return 0


def command_propose(args: argparse.Namespace) -> int:
    _print(propose(Path(args.project)))
    return 0


def command_choose(args: argparse.Namespace) -> int:
    _print(choose_plan(Path(args.project), args.direction))
    return 0


def command_apply(args: argparse.Namespace) -> int:
    changes = json.loads(Path(args.changes).read_text(encoding="utf-8"))
    _print(apply_edit(Path(args.project), changes))
    return 0


def command_export(args: argparse.Namespace) -> int:
    _print(export_movie(Path(args.project)))
    return 0


def command_cover(args: argparse.Namespace) -> int:
    _print(cover_frame(Path(args.project)))
    return 0


def command_motion(args: argparse.Namespace) -> int:
    _print(motion_hook(Path(args.project)))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="talkcut", description="TalkCut 单人口播粗剪。")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="检查骨架、ffmpeg，以及可选的语音包")
    doctor.set_defaults(func=command_doctor)

    setup = sub.add_parser("setup", help="把 ffmpeg 路径写入 runtime/config.json")
    setup.add_argument("--ffmpeg")
    setup.add_argument("--ffprobe")
    setup.add_argument("--whisper-model", default="small")
    setup.add_argument("--with-asr", action="store_true", help="可选安装 faster-whisper，不下载模型")
    setup.set_defaults(func=command_setup)

    importer = sub.add_parser("import", help="登记原片并做能量分段或可选转写")
    importer.add_argument("--video", required=True)
    importer.add_argument("--project", required=True)
    importer.add_argument("--transcript")
    importer.add_argument("--asr", default="energy", choices=["energy", "whisper"])
    importer.add_argument("--whisper-model", default="small")
    importer.set_defaults(func=command_import)

    reader = sub.add_parser("read", help="打印片段和 revision")
    reader.add_argument("--project", required=True)
    reader.set_defaults(func=command_read)

    planner = sub.add_parser("propose", help="按方法论钩子给一个轻量方向，不导出")
    planner.add_argument("--project", required=True)
    planner.set_defaults(func=command_propose)

    chooser = sub.add_parser("choose-plan", help="记下用户选定的方向")
    chooser.add_argument("--project", required=True)
    chooser.add_argument("--direction", required=True)
    chooser.set_defaults(func=command_choose)

    apply = sub.add_parser("apply", help="按 edit contract 粗剪，含逐词去气口")
    apply.add_argument("--project", required=True)
    apply.add_argument("--changes", required=True)
    apply.set_defaults(func=command_apply)

    motion = sub.add_parser("motion", help="记下 Remotion 钩子，本轮不渲染动效")
    motion.add_argument("--project", required=True)
    motion.set_defaults(func=command_motion)

    cover = sub.add_parser("cover", help="从保留片段抽一帧封面")
    cover.add_argument("--project", required=True)
    cover.set_defaults(func=command_cover)

    export = sub.add_parser("export", help="导出可播放的 mp4")
    export.add_argument("--project", required=True)
    export.set_defaults(func=command_export)
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    if not argv or argv[0] in {"-h", "--help"}:
        parser.print_help()
        return 0
    try:
        args = parser.parse_args(argv)
        return args.func(args)
    except TalkCutError as exc:
        print(f"TalkCut：{exc}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"TalkCut：JSON 无法解析：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
