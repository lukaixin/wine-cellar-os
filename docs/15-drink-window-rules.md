# 适饮期规则与酒窖健康分

最后更新：2026-06-13

本文说明本地 Alpha 版本的适饮期规则引擎和 Dashboard 酒窖健康分。当前实现是透明规则，不是 AI 判断，也不接入专家数据库、价格 API 或外部网站。

## 数据来源

- 适饮期来自 `Vintage.default_drink_from` 和 `Vintage.default_drink_to`。
- 置信度来自 `Vintage.drink_window_confidence`，目前只作为展示和候选信息，不参与评分加权。
- 当前年份使用后端服务器日期。
- 规则只读取现有字段，不直接修改 `Bottle`、`Vintage` 或库存 ledger。

## 状态定义

| 状态 | 含义 |
| --- | --- |
| `UNKNOWN` | 缺少开始年或结束年，无法判断。 |
| `TOO_EARLY` | 当前年份早于开始年前一年。 |
| `ENTERING` | 当前年份是开始年前一年，适合提前关注。 |
| `IN_WINDOW` | 当前年份位于开始年到结束年之间，含边界。 |
| `LATE` | 当前年份刚超过结束年一年，需要优先检查。 |
| `PAST` | 当前年份超过结束年一年以上，视为过期风险。 |

## Dashboard 输出

`/api/dashboard/summary` 保留原有字段，并新增：

- `available_bottles` / `unavailable_bottles`
- `drink_window_summary`
- `upcoming_drink_candidates`
- `past_window_risks`
- `cellar_health_score`

`drink_window_counts` 仍保留旧的四类字段以兼容既有 UI/测试：

- `entering` = `ENTERING + IN_WINDOW`
- `past` = `LATE + PAST`
- `without` = `UNKNOWN`
- `future` = `TOO_EARLY`

## 酒窖健康分

健康分是 0-100 的本地运营提示，由以下因子加权生成：

- 适饮期覆盖率：在库酒中有完整适饮期的比例。
- 过期风险：`LATE` 和 `PAST` 在库酒越多，分数越低。
- 酒柜容量压力：按位置容量和当前占用计算，接近满仓会降分。
- 可用库存平衡：可用在库酒过少或不可用比例过高会降分。

该评分只用于提醒用户整理库存和检查酒况，不代表专业品鉴、估值、投资或购买建议。

## 非目标

- 不做 Wine-Searcher 或其他受限网站抓取。
- 不接入真实 AI/OCR 判断适饮期。
- 不生成采购推荐或投资建议。
- 不绕过库存 ledger 修改瓶子状态。
