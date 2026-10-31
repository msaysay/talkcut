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
from engine.font_setup import ensure_fonts
from engine.layout_plan import (
    apply_agent_roles,
    build_plan,
    load_rules,
    load_script,
    sentences_from_project,
    write_agent_request,
    write_plan,
)
from engine.motion import render_cover_still, render_motion
from engine.reel import render_layout_reel
from engine.pipeline import (
    apply_edit,
    choose_plan,
    cover_frame,
    export_movie,
    import_media,
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
    "engine/motion.py",
    "motion-pack/presets/clean-knowledge/preset.json",
    "motion-pack/presets/gold-line/preset.json",
    "motion-pack/presets/opus-clean/preset.json",
    "motion-pack/presets/opus-punch/preset.json",
    "motion-pack/presets/card-knowledge/preset.json",
    "motion-pack/presets/eva-morph-v/preset.json",
    "motion-pack/guide.json",
    "pipeline/contracts/layout-plan.schema.json",
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
    motion = ROOT / "motion-pack" / "node_modules" / "remotion"
    presets = [path.name for path in (ROOT / "motion-pack" / "presets").iterdir() if (path / "preset.json").is_file()]
    print("ok  动效预设 " + "、".join(presets))
    if motion.is_dir():
        print("ok  motion-pack 的 Remotion 已安装。motion --preset 会渲染竖屏成片。")
    else:
        print("注意  motion-pack 依赖未安装。粗剪仍可 FFmpeg 导出；动效需在 motion-pack/ 执行 npm install。")
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
    if args.fonts:
        found = ensure_fonts()
        print("字体已在 runtime/fonts：" + ", ".join(sorted(found)))
    if args.vision:
        from engine.cutout import SEGMENTER_NAME, SEGMENTER_URL
        from engine.safe_zones import MODEL_NAME, MODEL_URL
        from engine.runtime import REPO
        import urllib.request

        models = REPO / "runtime" / "models"
        models.mkdir(parents=True, exist_ok=True)
        for name, url in ((MODEL_NAME, MODEL_URL), (SEGMENTER_NAME, SEGMENTER_URL)):
            dest = models / name
            if not dest.is_file():
                print(f"下载 {name}")
                urllib.request.urlretrieve(url, dest)
            print(f"ok  {dest}")
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
    if args.via == "remotion":
        if not args.preset:
            raise TalkCutError("export --via remotion 需要 --preset。")
        _print(render_motion(Path(args.project), args.preset, music=Path(args.music) if args.music else None, bpm=args.bpm, orientation=args.orientation))
        return 0
    _print(export_movie(Path(args.project)))
    return 0


def command_cover(args: argparse.Namespace) -> int:
    if args.via == "remotion":
        _print(render_cover_still(Path(args.project), args.preset, title=args.title))
        return 0
    _print(cover_frame(Path(args.project)))
    return 0


def command_plan(args: argparse.Namespace) -> int:
    folder = Path(args.project).expanduser().resolve()
    folder.mkdir(parents=True, exist_ok=True)
    rules = load_rules()
    if args.script:
        sentences = load_script(Path(args.script))
    else:
        from engine.store import load

        sentences = sentences_from_project(load(folder))
    video = str(Path(args.video).expanduser().resolve()) if args.video else None
    if args.classify == "agent" and not args.roles:
        _print(write_agent_request(folder, sentences, rules))
        return 0
    if args.roles:
        sentences = apply_agent_roles(sentences, Path(args.roles), rules)
    plan = build_plan(sentences, args.orientation, rules, video=video, classify=args.classify, bpm=args.bpm or 96)
    target, table = write_plan(folder, plan)
    print(table.read_text(encoding="utf-8"))
    _print({"plan": str(target), "table": str(table), "items": len(plan["items"]), "orientation": plan["orientation"]})
    return 0


def command_motion(args: argparse.Namespace) -> int:
    if args.reel:
        if not args.video:
            raise TalkCutError("版式合集需要 --video，先运行 examples/fetch_stock.py。")
        _print(render_layout_reel(Path(args.project), Path(args.video), args.orientation, args.preset))
        return 0
    _print(
        render_motion(
            Path(args.project),
            args.preset,
            music=Path(args.music) if args.music else None,
            bpm=args.bpm,
            lock=args.lock,
            orientation=args.orientation,
            layout=args.layout,
            stills=args.stills,
        )
    )
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
    setup.add_argument("--fonts", action="store_true", help="下载 OFL 字体到 runtime/fonts")
    setup.add_argument("--vision", action="store_true", help="下载 Apache-2.0 的 MediaPipe 人脸和分割模型")
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

    sentence_plan = sub.add_parser("plan", help="按句子生成可手改的 layout-plan.json")
    sentence_plan.add_argument("--project", required=True)
    sentence_plan.add_argument("--orientation", choices=["vertical", "landscape"], default="vertical")
    sentence_plan.add_argument("--classify", choices=["rules", "agent"], default="rules")
    sentence_plan.add_argument("--script", help="句子时间轴 JSON，例如 examples/demo-script.json")
    sentence_plan.add_argument("--video", help="成片将使用的原片路径，写入计划")
    sentence_plan.add_argument("--roles", help="宿主模型写回的角色 JSON")
    sentence_plan.add_argument("--bpm", type=float, default=96)
    sentence_plan.set_defaults(func=command_plan)

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

    motion = sub.add_parser("motion", help="用 Remotion 预设渲染竖屏字幕和配乐")
    motion.add_argument("--project", required=True)
    motion.add_argument("--preset", required=True, help="card-knowledge、eva-morph-v、opus-clean、opus-punch、clean-knowledge 或 gold-line")
    motion.add_argument("--stills", action="store_true", help="只渲每句中点静帧，确认后再去掉这个参数渲全片")
    motion.add_argument("--orientation", choices=["vertical", "landscape"], default="vertical")
    motion.add_argument("--music", help="用户自带的 BGM；省略则不配乐，只保留人声")
    motion.add_argument("--bpm", type=float, help="节拍；省略时从配乐检测")
    motion.add_argument("--lock", action="store_true", help="把该预设写进 presets/approved.json")
    motion.add_argument("--layout", help="整段使用一个版式，例如 v2 或 h4")
    motion.add_argument("--reel", action="store_true", help="渲染包含每种版式的短合集")
    motion.add_argument("--video", help="合集使用的口播原片，不从工程粗剪里取")
    motion.set_defaults(func=command_motion)

    cover = sub.add_parser("cover", help="抽封面帧，或渲染 Remotion 封面静帧")
    cover.add_argument("--project", required=True)
    cover.add_argument("--via", choices=["frame", "remotion"], default="frame")
    cover.add_argument("--preset", default="clean-knowledge")
    cover.add_argument("--title")
    cover.set_defaults(func=command_cover)

    export = sub.add_parser("export", help="FFmpeg 直出，或 --via remotion 合成竖屏成片")
    export.add_argument("--project", required=True)
    export.add_argument("--via", choices=["ffmpeg", "remotion"], default="ffmpeg")
    export.add_argument("--preset")
    export.add_argument("--music")
    export.add_argument("--bpm", type=float)
    export.add_argument("--orientation", choices=["vertical", "landscape"], default="vertical")
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
