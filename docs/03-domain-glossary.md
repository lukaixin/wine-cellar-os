# 领域词汇表

## Producer / 生产者

酒庄、酒厂、品牌、酒商或生产者。示例：Château Lafite Rothschild。

## Wine / 酒款

不含年份的抽象酒款。示例：Château Lafite Rothschild Grand Vin。

## Vintage / 年份酒款

酒款与年份的组合。示例：Château Lafite Rothschild Grand Vin 2010。

## Bottle / 单瓶实例

用户库存里的某一瓶具体酒，包含购买价、来源、位置、状态、照片等。

## Bottle format / 瓶型容量

750ml、375ml、1500ml、3000ml 等。

## Cellar / 酒柜或酒窖

物理存储空间。可以是恒温酒柜、地下酒窖、散存区域、箱装区域。

## Location / 位置

某个酒柜中的具体位置，例如 A柜 / 第 3 层 / 第 5 格 / 左后。

## InventoryTransaction / 库存事件

任何改变库存状态、数量、位置或可用性的事件。

类型包括：

- purchase_in
- gift_in
- manual_in
- drink_out
- gift_out
- sell_out
- transfer
- damage
- lost
- stocktake_adjustment
- return_out
- return_in

## DrinkWindow / 适饮窗口

建议饮用起止时间。必须允许来源和置信度。

## ValuationSnapshot / 估值快照

某一时间点对某个 vintage + bottle size 的市场参考价格记录。

## Canonicalization / 标准化

将多语言、多别名、多写法的酒名归并到同一个标准 Producer/Wine/Vintage。

## Confidence / 置信度

用于 AI 识别、适饮期、价格解析等不确定信息。枚举建议：low / medium / high。
