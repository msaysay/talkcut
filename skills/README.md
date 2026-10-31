# skills

Codex 和 WorkBuddy 加载**同一份**技能：`talkcut/SKILL.md`。不要为每个宿主复制一份流程，也不要把命令改成两套。

技能描述的是宿主无关的顺序：

```text
import → propose → 用户选定 → choose-plan → apply → motion → cover → export
```

CLI 在仓库里的位置固定为 `pipeline/cli/talkcut.py`。工作目录是 **TalkCut 仓库根**，不是技能被拷贝到的安装目录。

## Codex

把目录 `skills/talkcut` 指给 Codex 的 skills 路径，常见位置是 `~/.codex/skills/talkcut`（以本机 Codex 配置为准）。也可以在仓库对话里直接让代理阅读 `skills/talkcut/SKILL.md`。

Codex 读取 frontmatter 里的 `name` 与 `description`。流程以正文为准。

## WorkBuddy

把 `skills/talkcut` 作为技能目录导入。WorkBuddy 还会读 frontmatter 里的 `display_name` 与中英文描述。

本骨架没有把 CLI 再复制进技能目录。在 WorkBuddy 里执行命令时，先进入 TalkCut 仓库根，再调用 `python3 pipeline/cli/talkcut.py …`。

## 两边都要遵守的门

第 1 段 `propose` 只出方向。用户明确选定一个方向之前，不能 `choose-plan`，不能 `export`。字幕和画面标题是两个独立开关，用户没说的保持关闭。

`doctor` 目前只检查骨架文件。`setup` 以及剪辑子命令都会说明尚未实现并以非 0 退出。宿主应把这个结果告诉用户，不要改说成已经出片。
