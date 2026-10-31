# presets

动效与配乐的预设目录。当前只有这份说明，没有模板文件，也没有 `approved.json`。

## 计划中的两类预设

1. **鼓点风 BGM**（`bgm/`）  
   用节奏型配乐托住口播，而不是铺一条恒定音量的背景。预设描述拍点、段落（开 / 展 / 收）和 ducking，不把音频时间码交给模型现编。

2. **字幕 MG**（`captions/`）  
   可复用的字幕动效：前 3 秒钩子关键词、数字放大、金句、列表序号、CTA 口令。主色不超过 3 种。名片条单独放在 `nameplate/`。

## 锁定

用户认可某一套模板之后，把预设 id 与版本写入 `presets/approved.json`（尚未创建）。之后的片子默认沿用这套，直到用户明确要求更换。

锁定文件预期字段：

```json
{
  "version": 1,
  "bgmPreset": "drum-beat-default",
  "captionPreset": "talking-head-mg",
  "nameplatePreset": "credibility-left",
  "lockedAt": "ISO-8601"
}
```

未锁定时，第 3 段只允许使用占位合成，不能假装已经套上鼓点或字幕动效。
