# ADR-0003：价格模块采用 Provider Adapter

## 状态

Accepted.

## 背景

葡萄酒价格数据来源复杂，可能来自手动录入、酒商报价、截图、CSV、授权 API、拍卖记录或第三方平台。不同来源的授权、地区、币种、税费和可信度不同。

## 决策

价格模块采用 provider adapter。核心系统只依赖统一的 `ValuationSnapshot`，不依赖某个外部平台页面结构。

## 初始 Provider

- ManualPriceProvider
- CsvImportPriceProvider
- ScreenshotNoteProvider
- LinkNoteProvider

## 禁止

- 绕过访问限制。
- 批量抓取受限平台。
- 将未经授权的数据做成商业化数据库。

## 后果

优点：

- 合规风险更低。
- 后续可接授权数据源。
- 不把核心业务绑死在某个平台。

缺点：

- MVP 自动化程度较低。
- 需要用户手动确认价格。
