# presets

一套预设一个文件夹。`preset.json` 管画幅、颜色、字号、字体角色和配乐音量。旁边的组件只把这份 JSON 交给 `TalkingHead`。不要另写一套字幕组件。

| 文件夹 | 合成 id | 动效 | 说明 |
|---|---|---|---|
| `opus-clean/` | `opus-clean` | `settle` | 紧凑知识口播。字幕两行内完整落下，钩子、正文、数字用不同字体角色 |
| `opus-punch/` | `opus-punch` | `slash` | 数字从左右切片砍入后锁成完整数字。金句和钩子仍然整句可读 |
| `clean-knowledge/` | `clean-knowledge` | `fade` | 早一版干净知识口播 |
| `gold-line/` | `gold-line` | `beat-punch` | 早一版金句。顶栏闪动只在这份预设上 |
| `cover/` | `cover-still` | — | 标题静帧，各预设共用 |

`opus-clean` 和 `opus-punch` 是当前口播审美。旧的两套预设仍可渲染。

## 字幕

`engine/motion.py` 的 `split_caption_phrases` 先按标点和停顿（省略号、破折号只当作切点，不会留在屏幕上）切开，过长的一句再在「的 / 了 / 是」这类字后面切开。每条都是完整片段，时间不重叠。

`CaptionLayer` 同一时刻只画当前这一条。放得下就一行；放不下就换到最多两行，字号略缩小。不使用 `text-overflow: ellipsis`，也不在末尾补 `…`。退出时淡出，然后清空。

## 字体角色

渲染时从 `runtime/fonts` 拷进工程，CSS 家族名是角色名，不是字体商品名。

| 角色 | CSS | 用途 |
|---|---|---|
| body | `TC Body` | 正文 |
| hook | `TC Hook` | 钩子、行动号召 |
| cover | `TC Cover` | 封面和版式标题 |
| gold | `TC Gold` | 金句 |
| number | `TC Number` | 数字。`opus-punch` 里数字砍入后仍显示完整数字 |
| note | `TC Note` | 图文卡上的短注 |
| fallback | `TC Fallback` | 缺字回退 |

来源和 OFL 许可见 `THIRD_PARTY_NOTICES.md`。

## 版式

版式不在预设里写死。`plan` 按 `methodology/layout-rules.json` 给每句一个版式，`motion` 读取 `layout-plan.json`。

竖屏 `v1`–`v6`：全屏标题、圆形画中画、右下圆角、上下分屏、字在人身后、横幅。横屏 `h1`–`h5`：三分之一、左人右板、约 380px 画中画、下三分之一、缓慢推近。人脸安全区在 `safe-zones.json`。图文卡只放角色标题，不把整句再画一遍。

圆形画中画的位置参考 [Vibetool/talking-head-video](https://github.com/Vibetool/talking-head-video)（MIT）的 PiP 想法，实现是这里自己的。

## 可选配乐

默认没有 BGM。不传 `--music` 时不生成节拍器或鼓床，`musicFile` 为 null，成片只留粗剪人声。

两条接入方式，都要显式传入文件：

1. 用户自带。`motion --music <文件>` 或 `export --via remotion --music <文件>`。wav、mp3、m4a 会转成工程里的 `music.wav`。
2. 一条可商用曲。`python3 examples/fetch_music.py` 下载 Kevin MacLeod 的 Local Forecast（CC BY 4.0，需署名）到 `runtime/music/`，再把打印出的路径传给 `--music`。文件不进 git。

传入之后，人声仍在 `OffthreadVideo` 上。配乐是单独一层，说话时用 `speechVolume`，空隙用 `gapVolume`，行动号召再用 `ctaVolume`。只压低配乐，不替换人声。

## 对标

只采用 MIT 项目的思路，不把它们的源码拷进仓库。

- [Vibetool/talking-head-video](https://github.com/Vibetool/talking-head-video)：圆形画中画，讲解时人脸让开图卡。
- [neutral-Stage/remotion-captioneer](https://github.com/neutral-Stage/remotion-captioneer)：字幕样式包。这里的预设 JSON 是同一类数据，pill 和关键词高亮是自己画的。
- [GovinduSasanka/opus-motion-library](https://github.com/GovinduSasanka/opus-motion-library)：从 Opus 口播短片里抽出的动效。`opus-punch` 的数字砍入对应其中的 slice-assemble / number-counter：切片飞入后锁成完整数字，长句则换行并缩小，不用省略号。

满意后：

```bash
python3 pipeline/cli/talkcut.py motion --project <工程> --preset opus-clean --lock
```

这会写入 `presets/approved.json`。
