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
