# Attribution and third-party components

TalkCut's code is MIT. Third-party components keep their own licenses. MIT does not relicense FFmpeg, speech models, or media you bring in.

## Sayframe

The local edit kernel is ported from [sayframe](https://github.com/msaysay/sayframe), which is MIT.

```
MIT License

Copyright (c) 2026 SAYFRAME contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

Sayframe attributes part of the project-local editing approach to OpenFilm. For that retained material, the upstream notice is:

```
MIT License

Copyright (c) 2026 OpenFilm contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Runtime dependencies

TalkCut does not bundle these. `setup` records ffmpeg if it is already on PATH. `setup --with-asr` can install the Python package; the speech model is downloaded by that library on first use, not by doctor.

| Component | Upstream | License / notice |
| --- | --- | --- |
| FFmpeg | https://ffmpeg.org/legal.html | LGPL or GPL depending on the build you install |
| faster-whisper | https://github.com/SYSTRAN/faster-whisper | MIT. Optional. Model files have their own terms |
| Whisper model weights | https://github.com/openai/whisper | See the model card for the size you choose |
| SenseVoice | https://github.com/FunAudioLLM/SenseVoice | Not downloaded by TalkCut. Optional upstream of sayframe's aligner; see that model card if you use it yourself |

PyAV, ONNX Runtime, and a SenseVoice ONNX build are sayframe setup dependencies. This port's default path uses ffmpeg plus the Python standard library, and does not fetch those packages.

## Remotion

`motion-pack/` depends on [Remotion](https://www.remotion.dev/) 4.0.539 (`remotion` and `@remotion/cli`). Remotion is source-available, not MIT.

- Individuals, non-profits, and for-profit organizations with up to 3 employees may use it to create videos free of charge, including commercial videos.
- Larger for-profit companies need a company license: https://www.remotion.pro/license
- Terms: https://www.remotion.dev/docs/license

TalkCut does not relicense Remotion. Rendering calls the Remotion CLI; it does not vendor Remotion's source.

## Motion references

These MIT projects informed layout and caption motion. Their source is not copied into this repository.

| Project | License | What TalkCut uses from it |
| --- | --- | --- |
| [Vibetool/talking-head-video](https://github.com/Vibetool/talking-head-video) | MIT | Circular PiP placement while a graphic takes the frame |
| [neutral-Stage/remotion-captioneer](https://github.com/neutral-Stage/remotion-captioneer) | MIT | Preset-shaped caption styles (pill, keyword highlight) |
| [GovinduSasanka/opus-motion-library](https://github.com/GovinduSasanka/opus-motion-library) | MIT | Number slice-in and wrapping long lines down to a readable size |

## Optional music

`examples/fetch_music.py` can download Kevin MacLeod, "Local Forecast" (incompetech.com), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The file is not committed. Credit that title and author if you use it. Omitting `--music` adds no music and no generated drum bed.

## Fonts (OFL-1.1)

`setup --fonts` downloads these into `runtime/fonts`. The files are not committed. License texts are in `motion-pack/fonts/licenses/`. CSS uses role names (`TC Body`, `TC Hook`, …). The font files themselves are unmodified, so reserved font names stay inside the files.

| Role | Family | Source |
| --- | --- | --- |
| 正文字幕 | Douyin Sans（抖音美好体） | https://github.com/bytedance/fonts |
| 生僻字回退 | Noto Sans SC | https://github.com/notofonts/noto-cjk |
| 强调 / 钩子 | Smiley Sans（得意黑） | https://github.com/atelier-anchor/smiley-sans |
| 封面 / 大字钩子 | ZCOOL QingKe HuangYou（站酷庆科黄油体） | https://github.com/googlefonts/zcool-qingke-huangyou |
| 金句 | Noto Serif SC Black（思源宋体） | https://github.com/notofonts/noto-cjk |
| 数字 | Bebas Neue | https://github.com/google/fonts OFL `bebasneue` |
| 数字备选 | Oswald | https://github.com/google/fonts OFL `oswald` |
| 手写批注 | LXGW Marker Gothic（霞鹜漫黑） | https://github.com/lxgw/LxgwMarkerGothic |

Not used: 阿里巴巴普惠体, MiSans, 钉钉进步体, 优设标题黑, 庞门正道, HarmonyOS Sans, DIN.

If those downloads are missing, render falls back to a local CJK font such as Droid Sans Fallback (Apache-2.0) when it is installed.

## Vision models (Apache-2.0)

`setup --vision` downloads MediaPipe BlazeFace short-range and the selfie segmenter. They are not Robust Video Matting. Layout code in this repo is original. Public projects were used only as layout references (circle PiP, corner mask, split frame, lower third, landscape strip, number motion). Their source was not copied.

## Sample footage

`examples/fetch_stock.py` downloads Pexels video 8048443 (a person talking to camera). Pexels License allows commercial use. The mp4 is not committed. https://www.pexels.com/video/woman-talking-in-front-of-the-camera-8048443/
