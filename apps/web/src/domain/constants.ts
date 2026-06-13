export type Page = "dashboard" | "bottles" | "detail" | "add" | "import" | "label" | "cellar" | "transactions";

export type BottleAction = "MOVE" | "CONSUME" | "GIFT" | "DAMAGE" | "ADJUST";

export const statusLabel: Record<string, string> = {
  in_stock: "在库",
  drunk: "已饮用",
  gifted: "已送礼",
  damaged: "损耗",
  lost: "盘亏",
  returned: "已退回",
  sold: "已售出",
};

export const transactionLabel: Record<string, string> = {
  IN: "入库",
  MOVE: "移动",
  CONSUME: "饮用",
  GIFT: "送礼",
  DAMAGE: "损耗",
  ADJUST: "盘点调整",
};

export const drinkWindowLabel: Record<string, string> = {
  entering: "正在适饮",
  past: "已过适饮",
  without: "未填适饮期",
  future: "尚未到期",
};

export function pageTitle(page: Page): string {
  return {
    dashboard: "Dashboard",
    bottles: "藏酒列表",
    detail: "酒瓶详情",
    add: "新增入库",
    import: "CSV 导入",
    label: "酒标入库",
    cellar: "酒柜地图",
    transactions: "Transaction",
  }[page];
}
