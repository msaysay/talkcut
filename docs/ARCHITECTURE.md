# TalkCut 架构

TalkCut 是单人口播的四段流水线。宿主（Codex 或 WorkBuddy）负责理解和确认。切点、对齐和编码在 `engine/`。字幕动效和鼓点配乐仍是 Remotion 包，粗剪导出还不调用它。

## 总览

```mermaid
flowchart TD
  subgraph hosts [宿主]
    codex[Codex]
    workbuddy[WorkBuddy]
  end
  skill["skills/talkcut/SKILL.md"]
  codex --> skill
  workbuddy --> skill
  skill --> cli["pipeline/cli/talkcut.py"]
  method["methodology/ 脱敏方法论"]
  contracts["pipeline/contracts/"]
  cli --> s1["1 解析与方向"]
  method --> s1
  contracts --> s1
  s1 --> gate{"用户确认方向"}
  gate -->|继续改方案| s1
  gate -->|选定| s2["2 粗剪"]
  s2 --> s3["3 动效与配乐"]
  s3 --> s4["4 成片"]
  engine["engine/ 日后移植 sayframe"]
  engine --> s1
  engine --> s2
  engine --> s4
  motion["motion-pack/ Remotion 新建"]
  motion --> s3
```

第 1 段可以多次出方案。确认之前没有粗剪、没有动效、没有导出。原片始终保留。

## 各段职责

| 段 | 谁来做 | 产物 |
|---|---|---|
| 1 解析与方向 | 宿主模型读方法论；引擎以后提供转写和对齐 | 方向建议，见 planning contract |
| 2 粗剪 | 引擎按切点启发式删气口、静音并重排 | 可撤销的粗剪工程 |
| 3 动效与配乐 | Remotion motion-pack | 锁定的 BGM 与字幕预设 id |
| 4 成片 | 引擎导出封面、标题和成片 | 一条成片路径 |

模型不填写音频时间码。合同里的证据是原句 id 和逐字引用。时间由对齐模块从原音算。

## 复用、改写、新建

上游是 [sayframe](https://github.com/msaysay/sayframe)（MIT）。

| 块 | 策略 | 说明 |
|---|---|---|
| `speech_alignment`、`audio_cuts`、`speech_cleanup`、`smart_pauses` | 已移植 | 气口和静音会在 `apply` 里切掉并进入导出 |
| `editor_export`、`video_finish` | 已移植可用的部分 | 成片打包和倍速校验。标题排版仍依赖上游其余模块 |
| `planning`、封面排版 | 改写为轻量实现 | `propose` 读方法论 JSON。封面命令只抽保留帧 |
| sayframe 里的课程向文稿与对应模块 | 不迁入 | 规则在 `methodology/` |
| 四段流水线与确认门 | 新建 | `apply` 必须 `confirmed: true`。动效单独成段 |
| `motion-pack/` | 新建，本轮未接入导出 | Remotion。`motion` 只记钩子 |
| `skills/talkcut/` | 新建 | 一份技能，Codex 与 WorkBuddy 都加载 |

移植文件保留 sayframe 的 MIT 版权声明。

## 数据

- 方法论的机器可读部分：`methodology/EDIT_PIPELINE_HOOKS.json`
- 方向建议：`talkcut-planning-v0`
- 确认后的修改：`talkcut-edit-v0`
- 动效锁定：将来写在 `motion-pack/presets/approved.json`

三份都还没有校验器。CLI 在实现 `propose` / `apply` 时再按合同拒绝缺字段和伪造 id。

## 宿主

Codex 与 WorkBuddy 的差别只在技能目录怎么挂。对话步骤、合同和 CLI 子命令相同，见 `skills/README.md`。

工作台界面、撤销重做和跨文件编排都不在本架构的第一刀里。MVP 范围见 `docs/ROADMAP.md`。
