# motion-pack

TalkCut 的 Remotion 动效包。粗剪 mp4 和字句时间从 CLI 进来，这里渲染竖屏 1080×1920。

## 安装

```bash
npm install
npm run typecheck
npm run compositions
```

## 预设

见 `presets/`。入口是 `src/index.ts`，合成 id：

- `clean-knowledge`
- `gold-line`
- `cover-still`

平时不要手跑渲染。用仓库根目录的：

```bash
python3 pipeline/cli/talkcut.py motion --project <工程> --preset clean-knowledge
```

CLI 会把粗剪和字体放进工程的 `motion/public/`，再执行 `remotion render`。

## 授权

Remotion 不是 MIT。个人和不超过 3 名员工的营利组织可以免费用它做片；更大的公司需要公司许可证。https://www.remotion.dev/docs/license

本包不改 Remotion 本体，也不把 Remotion 再授权成 MIT。
