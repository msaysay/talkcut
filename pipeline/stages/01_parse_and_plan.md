# 1 · 解析与方向

本段只回答「这条片子可以怎么剪」。不导出，不改原片，不套动效。

## 输入

- 一条单人口播原片（或已经准备好的音轨）
- `methodology/03-edit-directives.md`
- `methodology/EDIT_PIPELINE_HOOKS.json`
- `methodology/02-content-conversion.md` 里的开—展—收、框架、开头类型
- `methodology/01-business-ip-system.md` 里的营销三问与视频类型，用来判断这条片子的任务

## 做什么

1. 转写或能量分段，并给每个片段稳定 id。时间来自音轨或文稿，不由模型猜测切口。当前 `propose` 先给一个去气口方向；语义上的多方向仍由宿主模型按合同补全。
2. 判断 `video_type` 与 `journey_role`。
3. 给出 1 到 4 个方向。每个方向写清钩子句、开—展—收、支撑块、金句、数字、资格背书词、CTA、封面标题模式、建议保留的人味、建议删掉的无效段。
4. 按 `pipeline/contracts/planning-contract.json` 保存方案。

方向里的原话必须能在当前转写里逐字对上。

## 输出

- 带 id 的转写
- 一份规划方案（可含多个方向）

## 停在这里

把方向讲给用户，并单独确认两件事：要不要自动字幕、要不要画面标题。用户没说的选项保持关闭。

「帮我剪」不等于选定方向。用户选定之前，禁止进入第 2 段。

## 检查清单

与 `EDIT_PIPELINE_HOOKS.json` 的 `stage1_checklist` 相同：`video_type`、`journey_role`、`hook_candidate`、`opening_style`、`structure_blocks`、`support_blocks`、`gold_lines`、`numbers_to_punch`、`credibility_phrase`、`cta`、`cover_title_pattern`、`keep_human_moments`、`cut_candidates`。检测不到就写明未检测到。
