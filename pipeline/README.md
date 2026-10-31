# pipeline

`doctor` 和 `setup` 检查本机 ffmpeg。`import`、`apply`、`export` 会跑完一条粗剪。语音模型是可选的。

## 命令

在仓库根目录：

```bash
python3 pipeline/cli/talkcut.py doctor
python3 pipeline/cli/talkcut.py setup
python3 pipeline/cli/talkcut.py import --video "<原片>" --project "<空目录>"
python3 pipeline/cli/talkcut.py read --project "<工程>"
python3 pipeline/cli/talkcut.py propose --project "<工程>"
python3 pipeline/cli/talkcut.py choose-plan --project "<工程>" --direction rough-cleanup
python3 pipeline/cli/talkcut.py apply --project "<工程>" --changes changes.json
python3 pipeline/cli/talkcut.py export --project "<工程>"
```

`import` 默认 `--asr energy`。已有逐词时间用 `--transcript`。`--asr whisper` 需要先 `setup --with-asr`。

`propose` 只写 `proposal.json`，不生成成片。`apply` 要求 changes 里 `"confirmed": true`，并且 `revision` 与最近一次 `read` 一致。

`motion` 记下 `motion-pack/` 钩子。`cover` 在粗剪之后抽一帧。

没有口播原片时：

```bash
python3 examples/make_synthetic.py --out examples/out
```

## 合同

| 文件 | 作用 |
|---|---|
| `contracts/planning-contract.json` | 方向建议的字段。`propose` 写出其中的轻量子集 |
| `contracts/edit-contract.json` | `apply` 读取的修改。`removeWords` 和 `cleanup` 会改音轨 |

## 阶段说明

- `stages/01_parse_and_plan.md`
- `stages/02_rough_cut.md`
- `stages/03_motion_music.md`
- `stages/04_finish.md`
