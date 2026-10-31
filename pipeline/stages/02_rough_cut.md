# 2 · 粗剪

只在用户选定一个方向之后开始。目标是去掉不该留的气口和静音，并按方法论钩子重排，同时留下人味。

## 输入

- 用户选定的方向 id
- 第 1 段的转写与 revision
- `methodology/03-edit-directives.md` 的切点启发式
- `EDIT_PIPELINE_HOOKS.json` 的 `cut_heuristics`
- 修改正文遵守 `pipeline/contracts/edit-contract.json`

## 做什么

1. `choose-plan` 记录选定方向，以及字幕、标题两个独立开关。
2. 按优先级处理切点：钩子前的准备动作、长时间沉默、第三次以上的同义反复、与主任务无关的支线。
3. 默认保留笑、气口、自然停顿和情绪峰。同一段有多条 take 时，留情绪和对象感更好的一遍。
4. 成片开头 3 秒落在钩子的完整意群上。不要为了压时长把句子切碎，也不要加速。
5. 展段按支撑块切开。收段留下听得清的 CTA。

本段不做花哨转场，不上鼓点配乐。字幕强调可以在方案里标出，真正的 MG 在第 3 段。

## 输出

- 一份可撤销的粗剪工程（引擎移植之后）
- 开 / 展 / 收 在成片上的边界

## 尚未接入

气口检测、静音、对齐和跳切要等 `engine/` 从 sayframe 移植 `speech_alignment`、`audio_cuts`、`speech_cleanup`。在那之前 CLI 的 `apply` 会拒绝执行。
