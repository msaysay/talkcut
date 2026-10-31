# 3 · 动效与配乐

粗剪完成之后，用 Remotion 把成片收成竖屏 1080×1920：下三分之一字幕，人声底下的鼓点配乐。

## 输入

- 已 `apply` 的工程。没有 `export/final.mp4` 时，`motion` 会先用 FFmpeg 拼一版粗剪再往上叠
- `motion-pack/presets/<name>/preset.json` 和同目录的组件
- 可选的用户 BGM。不传文件时，生成一段无版权的节拍底乐，方便先看卡点

## 预设

| id | 用途 |
|---|---|
| `clean-knowledge` | 干净知识口播。字幕淡入，数字用强调色，配乐在人声时压低 |
| `gold-line` | 强节奏金句。节拍上轻微放大，顶栏闪动，金句带强调色下划 |

字幕角色来自 `methodology/EDIT_PIPELINE_HOOKS.json` 的 `caption_emphasis`：第一句是钩子，数字单独放大，`真正 / 金句` 走金句，`评论 / 私信 / 关注` 走 CTA 并再压低配乐。主色不超过 3 种。字幕离底边一截，不贴安全区。

中文字体在渲染时从本机拷进工程（优先 Droid Sans Fallback，或 `TALKCUT_FONT`）。仓库不内置字体文件。

## 按句选版式

渲染前运行 `plan`。它读 `methodology/layout-rules.json`，给每句一个角色和版式，写成可手改的 `layout-plan.json`，并打印表格。`motion` 和 `export --via remotion` 默认按这份计划画。`--classify agent` 只生成给宿主模型的 prompt 和 schema，TalkCut 不调用大模型。

## 画幅和版式

`--orientation vertical` 是 1080×1920，`landscape` 是 1920×1080。坐标按画幅比例算。

竖屏：`v1` 全屏加人脸上方标题，`v2` 圆形画中画，`v3` 收到右下圆角（底部至少 140px），`v4` 上图下文，`v5` 字在人身后（MediaPipe 自拍分割，不是 RVM），`v6` 横幅条带。

横屏：`h1` 人占三分之一，`h2` 左人右板，`h3` 约 380px 画中画，`h4` 下三分之一字幕条，`h5` 缓慢推近。

人脸每 0.5 秒检测一次，框外扩 18% 写入 `safe-zones.json`，字幕避开这块。抖音底部和右侧边距在 `preset.json` 的 `platformMargins`，以后用真机截图改数字。

合集：

```bash
python3 examples/fetch_stock.py
python3 pipeline/cli/talkcut.py motion \
  --project examples/out/reel-vertical \
  --preset clean-knowledge \
  --orientation vertical \
  --reel \
  --video examples/out/pexels-talking-head.mp4
```

横屏把 `orientation` 改成 `landscape`，预设可以换成 `gold-line`。

## 命令

```bash
python3 pipeline/cli/talkcut.py motion \
  --project <工程> \
  --preset clean-knowledge \
  --music <你的BGM> \
  --bpm 96
```

省略 `--music` 时使用生成的底乐。省略 `--bpm` 且自带了音乐时，按音量突发起伏检测节拍。

`--lock` 把预设 id 写进 `motion-pack/presets/approved.json`。满意之后下一条继续用这个名字，不要每条重做一套动画。

`export --via remotion --preset gold-line` 走同一条渲染。默认 `export` 仍是 FFmpeg 直出，不经过 Remotion。

封面静帧是 `cover --via remotion --preset clean-knowledge`。它只排标题，不代替字幕成片。

## 输出

- `export/motion-<preset>.mp4`
- `export/cover-<preset>.png`
- `motion/props.json`（给 Remotion 的时间轴）

## 授权

Remotion 对个人、3 人及以下营利组织、非营利组织免费，可用于做片。更大的公司商用需要公司许可证。见 `THIRD_PARTY_NOTICES.md`。
