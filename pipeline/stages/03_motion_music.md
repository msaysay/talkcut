# 3 · 动效与配乐

粗剪稳定之后，给成片套上可复用的节奏和字幕，而不是为这一条现做一套动画。

## 输入

- 第 2 段的工程与 revision
- `motion-pack/` 里已安装的 Remotion 包
- `motion-pack/presets/` 中用户选定或已经锁定的预设
- `caption_emphasis` 与 `visual_layout`（方法论 JSON）

## 做什么

1. 字幕 MG：钩子关键词、反认知句、数字、金句、列表序号、CTA 口令。字幕落在画面下三分之一，不贴底，不挡脸。
2. 资格背书词首次完整出现时，名片条约 2–4 秒，短视频通常不超过 2 次。
3. 鼓点风 BGM 按开—展—收换段落能量。人声始终听得清；CTA 前后再把音乐压低。
4. 用户认可这套模板后，把预设 id 写入锁定记录（见 `motion-pack/presets/README.md`）。下一条默认沿用，直到用户要求更换。

## 输出

- 选定的 `musicPreset` 与 `motionTemplate`（写回 edit contract 的 settings）
- 预览用的 Remotion 合成。最终编码仍在第 4 段

## 现在的骨架

`motion-pack` 只有占位合成 `TalkCutPlaceholder`。没有预设文件时，不要报告「已经配上鼓点」或「字幕动效已套用」。
