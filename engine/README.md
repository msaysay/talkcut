# engine

这里还没有剪辑代码。TalkCut 的本地剪辑能力准备从 [sayframe](https://github.com/msaysay/sayframe)（MIT）移植，而不是在本骨架里重写一遍声音对齐。

移植时保留 sayframe 的版权声明与 MIT 许可。上游仓库里绑定特定课程名的文稿和模块**不要**拷进来；剪辑决策改由本仓库 `methodology/` 驱动。

## 准备移植的模块

路径相对于 sayframe 仓库：

| TalkCut 需要的能力 | sayframe 模块 |
|---|---|
| `speech_alignment` | `engine/shared/speech_alignment.py` |
| `audio_cuts` | `engine/shared/audio_cuts.py` |
| `speech_cleanup` | `engine/shared/speech_cleanup.py` |
| `editor_export` | `engine/shared/editor_export.py` |
| `covers` | `engine/covers.py`，排版辅助在 `engine/shared/cover_layout.py` |
| `planning` | `engine/planning.py`，编辑规划在 `engine/shared/editor_planning.py` |

这六块分别对应：原音对齐、切口、口播清理、成片导出、封面、方向方案。第 2 段粗剪依赖前三块；第 1 段和第 4 段依赖 planning、covers、editor_export。

## 移植时多半还要一起看的邻居

不在本次骨架的拷贝范围内，但粗剪和导出很难只靠上表六份文件独立运行：

- `engine/shared/repeated_takes.py`：多条 take 里留情绪更好的一遍
- `engine/shared/smart_pauses.py`：停顿取舍
- `engine/shared/speech_seams.py`：切口接缝
- `engine/shared/music_mix.py`：人声与 BGM 的音量关系（鼓点预设本身在 `motion-pack/`）
- `engine/shared/editor_workflow.py`：工程状态与导出顺序

具体依赖以移植那一天的 sayframe 源码为准。不要按这份名单把整个 `engine/shared/` 一次性搬进来。

## 不在引擎里做的事

- Remotion 字幕 MG 和鼓点风 BGM 预设：`motion-pack/`
- 方法论规则：`methodology/`
- 宿主对话顺序：`skills/talkcut/SKILL.md`
