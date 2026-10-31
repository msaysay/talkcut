# engine

本机粗剪内核。可复用的部分来自 [sayframe](https://github.com/msaysay/sayframe)（MIT），版权声明在各文件头和 `THIRD_PARTY_NOTICES.md`。上游绑定特定课程目录的模块没有搬进来；剪辑决策用本仓库 `methodology/`。

运行入口是 `pipeline/cli/talkcut.py`，不读取任何宿主的安装目录。

## 现在能跑的路径

`import` → `read` →（`propose` 可先不做）→ `apply` → `export`

- 默认 `import --asr energy`：用音量把口播分成说话、气口、静音，不下载模型。
- `import --transcript words.json`：使用已有的逐词时间。
- `import --asr whisper`：可选。需要先 `setup --with-asr`。模型在第一次转写时由 faster-whisper 下载。
- `apply` 在 `confirmed: true` 之后真正切除 `removeWords`，以及 `cleanup` 里打开的气口、填充词和长静音。
- `export` 用 ffmpeg 拼出 `export/final.mp4`。这一步不经过 Remotion。

没有原片时，用 `examples/make_synthetic.py` 生成蜂鸣 + 气口 + 静音。

## 从 sayframe 移植的文件

| 文件 | 处理 |
|---|---|
| `shared/audio_cuts.py` | 原样移植。`apply` 用它把词和气口从片段里切掉 |
| `shared/smart_pauses.py` | 移植。`detect` 改为接收 ffmpeg 路径和缓存目录，不再要宿主对象 |
| `shared/acoustic_atoms.py` | 移植。FACT 规则内联在文件里，避免拉进整条复核链 |
| `shared/acoustic_restarts.py` | 原样移植 |
| `shared/render_spans.py` | 原样移植。导出前合并紧挨着的源时间 |
| `shared/disfluency_grammar.py` | 原样移植。自动删填充词时挡住正常语法衔接 |
| `shared/asr_coverage.py` | 原样移植 |
| `shared/media_paths.py` | 原样移植 |
| `shared/speech_alignment.py` | 只保留与宿主无关的对齐辅助。上游 `revise()` 里的本机模型路径已去掉 |
| `shared/video_finish.py` | 移植。导出只用其中的倍速校验；标题排版仍依赖上游其余文件 |
| `shared/editor_export.py` | 移植。成片打包用 `bundle()`。封面排版不在这条导出路径上 |
| `native_audio.py` | 按上游回执格式重写。接受时间行，不查找宿主安装位置 |

## 为了补上逐词删音而新写的部分

上游把逐词删除留在草稿里，导出会拒绝。TalkCut 在 `apply` / `export` 里执行：

| 文件 | 作用 |
|---|---|
| `acoustic.py` | 20ms 音量：说话 / 气口 / 静音 |
| `shared/speech_cleanup.py` | 把气口、填充词、长静音收成 `removeWords` |
| `cuts.py` | 调用移植的 `audio_cuts`，留下可播放片段 |
| `asr.py` | 可选 faster-whisper |
| `finish.py` | ffmpeg 拼 mp4，并调用 `editor_export.bundle` |
| `planning.py` | 读 `EDIT_PIPELINE_HOOKS.json`，给一个轻量方向 |
| `covers.py` | 从保留片段抽一帧。完整封面排版仍在上游 |

`motion` 命令只把 Remotion 包记到工程里，不渲染。

## 没有移植的部分

上游 `planning.py` 绑定课程方法目录，所以没有原样搬入。`engine/agent.py`、工作台，以及整条 `editor_workflow` 复核链也没有搬。那些文件会把剪辑决策拉回课程模块，并带上固定的本机模型路径。
