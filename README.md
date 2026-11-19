# acadowrite — 学术写作 Skill

生成**可编辑、事实可追溯**的学术稿件：每个数字、单位与论断都能回溯到底稿；材料不足处显式占位而不编造；同时交付 Markdown 与 Word。

## 解决什么问题

普通 Agent 的常见失败：数值、单位、样本量是模型自己补的；引用并不支撑所在句子；章节缺失却不说明；成稿无法继续编辑；摘要与结果、方法与步骤互相冲突。

## 安装与依赖

- Python 3.9+
- python-docx（DOCX 输出；缺失时降级并记录）
- 无需联网

```
acadowrite/
├── SKILL.md
├── README.md
├── GITHUB_URL.txt
├── references/
│   ├── fact-extraction.md
│   └── output-schema.md
├── examples/
│   ├── case.example.json
│   └── selftest-summary.md
└── scripts/
    ├── write.py
    └── check_facts.py
```

## 用法（最小示例）

```bash
python3 scripts/write.py       --case /input/case.json --work /app/work
python3 scripts/check_facts.py --case /input/case.json --work /app/work
```

输入示例：

```json
{
  "case_id": "demo",
  "task_type": "generate",
  "title": "Annealing temperature and perovskite conductivity",
  "audience": "材料方向研究生",
  "style": "中文、学术、简洁",
  "format": "markdown+docx",
  "facts": "样品在 100 C 退火后电导率为 1.5 S/cm。每组样本量 n=30。",
  "sections": ["Abstract", "Introduction", "Methods", "Results", "Discussion", "Conclusion", "References"],
  "references": ["Vaswani A. Attention is all you need. NeurIPS 2017."]
}
```

> 以上为**示意示例**，不是正式案例结果。

## 输出

| 文件 | 内容 |
|-|-|
| `manuscript.md` | 可编辑 Markdown（标题层级、项目符号保留） |
| `manuscript.docx` | 可编辑 Word |
| `fact_map.json` | 事实（数值+单位）→ 来源句；章节、参考文献、约束 |
| `revisions.json` | 修改记录与人工确认项 |
| `fact_check.json` | 一致性校验判决 |
| `result.json` | `case_id` / `status` / counts / uncertainty |

## 关键设计

- **事实优先**：只有含数字/单位的句子被当作事实，数值必须来自底稿。
- **缺失显式**：无支撑的章节留占位并列入确认项。
- **引用可核**：参考文献单列，不参与数值一致性检查。
- **双格式交付**：Markdown + DOCX。
- **校验拦截**：`check_facts.py` 拒绝底稿之外的数值。

## 局限

- 不写论文正文的论证展开（需模型补充）；
- 不判断文献真实性或方法学质量；
- 不做期刊排版。

## 许可与版本

- 版本：acadowrite 1.0.0
- 依赖：Python 3.9+、python-docx。
