# motion-pack

TalkCut 的 Remotion 动效包骨架。这里只保证依赖能安装、有一个竖屏占位合成，**还没有**鼓点配乐和字幕动效。

成片的第 3 段（动效与配乐）会调用本包。模板一经用户认可就锁定，不要每条片子重选一套节奏。

## 现在可以做的

在本目录：

```bash
npm install
npm run compositions
npm run typecheck
```

`npm run studio` 会打开 Remotion Studio，入口是 `src/index.ts`。占位合成 `TalkCutPlaceholder` 为 1080×1920、30fps、90 帧，用来确认工程能被 Remotion 读到。

## 预设放哪里

| 路径 | 以后放什么 |
|---|---|
| `presets/bgm/` | 鼓点风 BGM 的预设说明与音量包络。曲目用用户自备或明确可再分发的音频，本仓库不内置受版权保护的成曲 |
| `presets/captions/` | 字幕 MG：钩子大字、数字强调、金句、序号徽章、CTA 口令 |
| `presets/nameplate/` | 资格背书词名片条（中左、不挡脸，约 2–4 秒） |
| `presets/approved.json` | 已锁定模板的 id 与版本。文件尚未创建；锁定规则见 `presets/README.md` |

画面安全区与强调规则以 `methodology/03-edit-directives.md` 和 `methodology/EDIT_PIPELINE_HOOKS.json` 的 `caption_emphasis`、`visual_layout` 为准。BGM 默认躲在人声下面，收段 CTA 前后再压低。

## 和第 2、第 4 段的边界

粗剪和成片导出在 `engine/`，不经过本包。`talkcut motion` 只会把预设目录记到工程里。封面静帧由引擎抽帧；本包以后提供字幕和配乐节奏。
