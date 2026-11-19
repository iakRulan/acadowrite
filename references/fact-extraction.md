# 事实抽取与来源映射

## 事实定义

一条**事实**= 一个含数字的句子 + 该句中出现的全部数值/单位。

正则：`(?<![\w.])(\d+(?:\.\d+)?)\s*([a-zA-Z%/°µμ][a-zA-Z0-9%/°µμ]*)?`

- 数字 + 单位视为一组；单位可缺省。
- 同一句子去重；同句中相同数值只记一次。
- 不含数字的句子不作为确定性事实（ prose 由模型处理）。

## 事实结构

```json
{
  "sentence": "样品在 100 C 退火后电导率为 1.5 S/cm。",
  "values": [{"value": "100", "unit": "C"}, {"value": "1.5", "unit": "S/cm"}],
  "source": "fact_sheet"
}
```

## 分配规则

按句子关键词分配到章节：

| 章节 | 关键词 |
|-|-|
| Abstract | abstract, summary, overall |
| Introduction | background, introduction, previous, context |
| Methods | method, protocol, instrument, procedure, sample |
| Results | result, measured, observed, found, showed |
| Discussion | discussion, suggest, consistent, compared |
| Conclusion | conclusion, conclude, future |

未命中的事实归入 Results（若无 Results 则归入第一节）。

## 一致性校验

- 稿件正文（References 之前）出现的每个数值都必须在 `fact_map.json` 的 `values` 中。
- 参考文献列表中的年份不参与数值校验。
- 命中底稿外数值即 `valid=false`。

## 缺失处理

| 情况 | 处理 |
|-|-|
| 底稿为空 | confirmation「底稿为空」，status=partial |
| 章节无支撑 | 占位文本 + confirmation |
| 标题缺失 | confirmation，标题为「(标题待确认)」 |
| 改稿任务无草稿 | confirmation，回退为生成 |
