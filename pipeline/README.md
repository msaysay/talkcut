# pipeline

TalkCut 的流水线骨架：一份 CLI、两份合同、四段说明。引擎还没接上，所以除 `doctor` 以外的子命令都会拒绝执行。

## 命令

在仓库根目录：

```bash
python3 pipeline/cli/talkcut.py doctor
python3 pipeline/cli/talkcut.py --help
```

稳定子命令（技能按这个顺序写，实现以后不要改名）：

```text
doctor → setup → import → read → propose → choose-plan → apply → motion → cover → export
```

`propose` 只保存方向。用户确认之前不能 `choose-plan`，更不能 `export`。

## 合同

| 文件 | 对应阶段 | 上游借鉴 |
|---|---|---|
| `contracts/planning-contract.json` | 第 1 段方向建议 | sayframe `references/planning-contract.json` |
| `contracts/edit-contract.json` | 确认之后的粗剪修改 | sayframe `references/edit-contract.json` |

两份文件用字段说明表达形状，不是 JSON Schema，也还没有校验器。引用必须来自当前 `read` 的原句 id，不能把示例 id 当成这条片子的素材。

## 阶段说明

- `stages/01_parse_and_plan.md`
- `stages/02_rough_cut.md`
- `stages/03_motion_music.md`
- `stages/04_finish.md`
