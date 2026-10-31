# TalkCut 路线图

粗剪路径已经能从 `import` 走到 `export`：默认用能量分段去掉气口和长静音，并按词删掉单独的填充词。语义多方向、Remotion 预设和语音模型下载仍在后面。

## MVP

最小闭环是一条竖屏单人口播，从方向建议走到一条真实成片。范围按下面的顺序收，而不是把 sayframe 整仓搬进来。

1. **运行时检查**  
   `doctor` 能区分「骨架在」和「ffmpeg、本地 ASR 可用」。`setup` 只在技能自己的运行时目录准备依赖，缺 Python 或下载失败时说明原因，不改口称已经装好。

2. **导入与转写**  
   `import` 登记一条原片。`read` 返回带稳定 id 的原句，并带上这次的 revision 与 source hash。模型不猜时间码。

3. **方向建议（第 1 段）**  
   `propose` 读取 `methodology/`，按 `talkcut-planning-v0` 写出 1 到 4 个方向。此步不导出。

4. **确认门**  
   用户选定方向，并单独决定字幕与画面标题。未选定不能进入粗剪。

5. **粗剪（第 2 段）**  
   移植 `speech_alignment`、`audio_cuts`、`speech_cleanup`。去掉气口和过长静音，按钩子重排，保留笑和自然停顿。`apply` 使用最近一次 revision。

6. **动效槽位（第 3 段）**  
   motion-pack 至少有一个字幕预设和一个 BGM 槽位（音量包络可以先用占位，曲目由用户提供）。用户认可后把预设 id 锁定。人声不被音乐盖住。

7. **成片（第 4 段）**  
   移植 `planning`、`covers`、`editor_export`。输出封面建议、标题和一条成片。失败时留下原因，不把原片说成成片。

## MVP 不做

- 多人访谈、跨文件编排
- 完整鼓点曲库和整套字幕动效
- 把 sayframe 的 `engine/shared/` 全部拷入
- 把云端语音 API 当成默认转写
- 工作台 UI、撤销重做的完整产品化（引擎若自带撤销，移植时再暴露）

## 骨架之后、闭环之前

- 给 planning / edit 合同加校验，拒绝示例 id 和过期 revision
- `examples/single-speaker/` 放一条可再分发的口播，并写明预期产物
- `motion-pack/presets/approved.json` 的读写
- 封面三选一（用户选，助手不代选）

## 完成标准

一条授权过的单人口播走完 `import`、`read`、`propose`、用户选定、`choose-plan`、`apply`、`motion`、`cover`、`export`。成片前 3 秒是钩子原话，收段 CTA 听得清，且第 1 段的日志里没有导出文件。
