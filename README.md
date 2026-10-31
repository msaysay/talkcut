# TalkCut

单人口播自动剪辑。先根据转写和方法论给出剪辑方向；**你确认之后**才去气口、重排、套动效和配乐，最后出封面并导出。

> **TalkCut** is an open-source auto-editor for single-person talking-head videos. It turns a transcript plus a sanitized edit methodology into cut-direction proposals, then — only after you confirm — rough-cuts, applies a reusable Remotion motion pack, and finishes cover, title, and render.

## 产品定位

TalkCut 服务「一个人出镜、对着镜头把一件事说清楚」的成片，而不是多人访谈或剧情短片。

它把三块已经想清楚的东西接成一条流水线：

| 块 | 来自哪里 | 在 TalkCut 里做什么 |
|---|---|---|
| 本地剪辑引擎思路 | [sayframe](https://github.com/msaysay/sayframe)（MIT） | 转写对齐、去气口/静音、粗剪、封面与导出。本仓库暂不拷贝源码，见 `engine/README.md` |
| 剪辑方法论 | `methodology/` | 脱敏后的转化型口播规则：钩子、开—展—收、字幕强调、CTA、封面标题 |
| 动效与配乐 | `motion-pack/` | 新建的 Remotion 包：鼓点风 BGM + 字幕 MG。模板一旦认可就锁定 |

宿主不绑定一家。同一份技能 `skills/talkcut/SKILL.md` 给 **Codex** 和 **WorkBuddy** 用，差别只在技能目录怎么挂上，见 `skills/README.md`。

## 四段流水线

用户确认发生在第 1 段和第 2 段之间。第 1 段可以反复出方案，但**不导出、不改原片**。

```text
1 解析与方向    转写 + methodology → 剪辑方向建议
        ↓  你选定一个方向（以及字幕 / 标题开关）
2 粗剪          去掉气口和静音，按方法论钩子重排
3 动效与配乐    Remotion motion-pack：鼓点风 BGM + 字幕 MG；认可后锁定模板
4 成片          封面 + 标题 + 最终渲染
```

各段输入、输出和禁止事项写在 `pipeline/stages/`。方向建议与粗剪修改分别遵守：

- `pipeline/contracts/planning-contract.json`
- `pipeline/contracts/edit-contract.json`

字段形状借鉴 sayframe 的 `references/planning-contract.json` 与 `references/edit-contract.json`，并改成 TalkCut 的四段流程和 `methodology/` 用词。这里是文档化的最小合同，还不是校验器。

## 和 sayframe 的关系

[sayframe](https://github.com/msaysay/sayframe) 是上游灵感，许可证为 MIT。TalkCut 要借它已经跑通的**本地口播剪辑引擎**（对齐、切口、清理、规划、封面、导出），不借它仓库里的课程向文稿。

| | sayframe | TalkCut |
|---|---|---|
| 素材 | 访谈、课程、专家口播 | 单人口播 |
| 方法论 | 上游仓库自己的 references | 本仓库 `methodology/` 脱敏包 |
| 成片动效 | 引擎内标题/字幕 | 独立 Remotion `motion-pack/` |
| 确认点 | 选定方向后再导出 | 第 1 段与第 2 段之间必须确认；动效模板另行锁定 |
| 宿主 | 以 WorkBuddy 技能为入口 | Codex 与 WorkBuddy 加载同一份技能 |

尚未移植的模块名单见 `engine/README.md`。在移植发生之前，不要把本仓库说成「已经包含 sayframe」。

## Codex / WorkBuddy 双入口

两个宿主读的是同一份 `skills/talkcut/SKILL.md`，调用的是同一条 CLI：

```text
import → propose → （你选择）→ choose-plan → apply → motion → cover → export
```

- **Codex**：把 `skills/talkcut` 指到 Codex 的 skills 目录。
- **WorkBuddy**：把 `skills/talkcut` 当作技能目录导入。

不要为每个宿主复制一份流程。挂载方式写在 `skills/README.md`。

## 仓库地图

```text
methodology/     脱敏方法论（中文）与 EDIT_PIPELINE_HOOKS.json
motion-pack/     Remotion 包骨架，预设目录在 presets/
pipeline/        CLI 骨架、合同、四段说明
skills/talkcut/  宿主无关技能
engine/          占位说明：以后从 sayframe 移植哪些模块
examples/        单人口播样片预期（不含成片文件）
docs/            架构与 MVP 范围
```

## 以后怎么跑

骨架阶段可以做两件事：检查目录是否齐全，以及安装 motion-pack 依赖。`setup` 还不会安装 ffmpeg 或语音模型。

```bash
python3 pipeline/cli/talkcut.py doctor
python3 pipeline/cli/talkcut.py setup    # 会说明尚未实现，并以非 0 退出

cd motion-pack
npm install
npm run compositions
```

`import`、`propose`、`choose-plan`、`apply`、`motion`、`cover`、`export` 已留在 CLI 上，方便技能按稳定子命令来写，但都会明确退出并说明尚未实现。不要把 doctor 的通过理解成「可以出片」。

运行时准备（ffmpeg、本地 ASR、工程目录布局）留到 `setup` 实现时再写进 `docs/`。届时 doctor 应能区分「骨架在」和「剪辑依赖在」。

## 许可

本仓库采用 [MIT License](LICENSE)。若之后迁入 sayframe 源码，须保留其版权声明与本 MIT 许可声明。
