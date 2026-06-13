---
name: sample-inventory-profiler
description: Profile local sample inventory workbooks for Wine Cellar OS. Use when Codex needs a read-only structural scan of data/sample/WineList.xlsx or similar sanitized xlsx files before designing import mappings, normalization rules, or review notes.
---

# name

sample-inventory-profiler

## description

用于在实现导入、标准化或映射规则前，先对样例库存文件做只读体检。默认关注 `data/sample/WineList.xlsx` 的工作表结构、表头差异、空值、去重维度和基础分布。

## when to use

- 准备设计 CSV / Excel 导入映射前。
- 需要判断样例工作簿里哪些 sheet 真正适合导入。
- 需要快速识别 `Producer` / `Wine` / `Vintage` 列名、缺失率和脏数据风险。
- 需要给导入方案补充基于样例的证据，而不是拍脑袋假设。

## when not to use

- 不用于真实用户库存库或包含敏感数据的未脱敏文件，除非用户明确要求。
- 不用于正式入库、数据修复、schema 迁移或外部网站抓取。
- 不用于直接改写样例文件内容。

## required checks

- 先读取 `AGENTS.md`、`data/README.md`、`docs/04-data-model.md`。
- 只读分析，不修改 `data/sample/WineList.xlsx` 或任何数据库文件。
- 至少输出：sheet names、columns、row count、null counts、unique producer/wine/vintage counts、basic distributions。
- 标记异构 sheet、空 sheet、空白表头列和无法可靠识别的字段。
- 若使用脚本，优先运行 `python scripts/profile_wine_sample.py`，并在结果里写明分析路径。

## expected final output

- 一份样例文件结构画像。
- 一份候选导入 sheet / 字段映射建议。
- 一份需要人工决定的风险点或歧义清单。
