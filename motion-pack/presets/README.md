# presets

一套预设一个文件夹：`preset.json` 管颜色、字号、配乐音量，旁边的组件管怎么画。

| 文件夹 | 合成 id | 说明 |
|---|---|---|
| `clean-knowledge/` | `clean-knowledge` | 干净知识口播 |
| `gold-line/` | `gold-line` | 强节奏金句 |
| `cover/` | `cover-still` | 标题静帧，两条成片共用 |

`talkcut motion --preset <id>` 会读这里的 JSON，生成工程里的 `motion/props.json`，再调用 Remotion。

Codex 和 WorkBuddy 改同一份文件即可，不要另起一套流程。满意后：

```bash
python3 pipeline/cli/talkcut.py motion --project <工程> --preset clean-knowledge --lock
```

这会写入 `presets/approved.json`。配乐文件由用户自己提供；省略时只用生成的节拍底乐。
