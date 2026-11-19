# 输出字段字典

## `manuscript.md` / `manuscript.docx`

- `#` 标题、`##` 章节、`-` 项目符号
- 事实条目格式：`- 事实（值+单位, …）：来源句`
- 缺失章节：`_本节内容需依据底稿补充；底稿未提供，暂留占位。_`

## `fact_map.json`

| 字段 | 说明 |
|-|-|
| `case_id` / `task_type` | 任务标识与类型 |
| `title` / `audience` / `style` / `format` | 约束 |
| `facts[]` | `sentence` / `values[]{value,unit}` / `source` |
| `sections[]` | 需要的章节 |
| `references[]` | 参考文献 |
| `uncertainty[]` | 确认项 |

## `revisions.json`

| 字段 | 说明 |
|-|-|
| `revisions[]` | `type` / `detail`（改稿任务） |
| `confirmations[]` | `item` / `reason` / `action` |
| `docx_written` | DOCX 是否成功写出 |

## `fact_check.json`

`{valid, checks, issues[], case_id}`；checks 含 `numbers_in_manuscript`、`numbers_not_in_fact_sheet`、`required_sections`、`missing_sections`、`docx_present`、`docx_headings`、`confirmations`。

## `result.json`

| 字段 | 说明 |
|-|-|
| `case_id` / `task` / `status` | `academic-writing` |
| `deliverables` | markdown / docx / fact_map / revisions |
| `counts` | `facts` / `sections` / `references` / `confirmations` |
| `uncertainty` | 确认项 |
| `sources` / `changes` | |
