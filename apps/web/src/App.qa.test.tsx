import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

type Entity = Record<string, any>;

function makeServer() {
  let id = 1;
  const currentYear = 2026;
  const nextId = (prefix: string) => `${prefix}-${id++}`;
  const state = {
    producers: [] as Entity[],
    wines: [] as Entity[],
    vintages: [] as Entity[],
    cellars: [] as Entity[],
    locations: [] as Entity[],
    bottles: [] as Entity[],
    transactions: [] as Entity[],
    uploads: [] as Entity[],
  };

  function json(body: unknown, status = 200) {
    return new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  }

  function locationRead(location: Entity) {
    const cellar = state.cellars.find((item) => item.id === location.cellar_id);
    return { ...location, cellar_name: cellar?.name ?? null };
  }

  function classifyDrinkWindow(vintage?: Entity) {
    const drinkFrom = vintage?.default_drink_from ?? null;
    const drinkTo = vintage?.default_drink_to ?? null;
    if (!drinkFrom || !drinkTo) {
      return { status: "UNKNOWN", message: "未设置完整适饮期。", yearsUntil: null, yearsPast: null };
    }
    if (currentYear < drinkFrom - 1) {
      return { status: "TOO_EARLY", message: `距离适饮期开始还有 ${drinkFrom - currentYear} 年。`, yearsUntil: drinkFrom - currentYear, yearsPast: null };
    }
    if (currentYear < drinkFrom) {
      return { status: "ENTERING", message: "即将进入适饮期。", yearsUntil: drinkFrom - currentYear, yearsPast: null };
    }
    if (currentYear <= drinkTo) {
      return { status: "IN_WINDOW", message: "当前处于适饮期。", yearsUntil: 0, yearsPast: null };
    }
    if (currentYear === drinkTo + 1) {
      return { status: "LATE", message: "刚过建议适饮期，需要优先检查。", yearsUntil: null, yearsPast: 1 };
    }
    return { status: "PAST", message: `已超过建议适饮期 ${currentYear - drinkTo} 年。`, yearsUntil: null, yearsPast: currentYear - drinkTo };
  }

  function bottleRead(bottle: Entity): Entity {
    const vintage = state.vintages.find((item) => item.id === bottle.vintage_id);
    const wine = state.wines.find((item) => item.id === vintage?.wine_id);
    const producer = state.producers.find((item) => item.id === wine?.producer_id);
    const location = state.locations.find((item) => item.id === bottle.current_location_id);
    const cellar = state.cellars.find((item) => item.id === location?.cellar_id);
    const drinkWindow = classifyDrinkWindow(vintage);
    return {
      ...bottle,
      producer_name: producer?.name_original ?? null,
      producer_name_cn: producer?.name_cn ?? null,
      wine_name: wine?.name_original ?? null,
      wine_name_cn: wine?.name_cn ?? null,
      vintage_year: vintage?.vintage_year ?? null,
      is_non_vintage: vintage?.is_non_vintage ?? false,
      default_drink_from: vintage?.default_drink_from ?? null,
      default_drink_to: vintage?.default_drink_to ?? null,
      drink_window_confidence: vintage?.drink_window_confidence ?? null,
      drink_window_status: drinkWindow.status,
      drink_window_message: drinkWindow.message,
      years_until_drink_window: drinkWindow.yearsUntil,
      years_past_drink_window: drinkWindow.yearsPast,
      wine_type: wine?.type ?? null,
      country: wine?.country ?? producer?.country ?? null,
      cellar_name: cellar?.name ?? null,
      location_code: location?.code ?? null,
    };
  }

  function transactionRead(transaction: Entity) {
    const bottleEntity = state.bottles.find((item) => item.id === transaction.bottle_id);
    if (!bottleEntity) throw new Error(`Missing bottle for transaction ${transaction.id}`);
    const bottle = bottleRead(bottleEntity);
    const from = state.locations.find((item) => item.id === transaction.from_location_id);
    const to = state.locations.find((item) => item.id === transaction.to_location_id);
    return {
      ...transaction,
      bottle_label: `${bottle.wine_name ?? "Wine"} ${bottle.is_non_vintage ? "NV" : bottle.vintage_year}`,
      from_location_code: from?.code ?? null,
      to_location_code: to?.code ?? null,
    };
  }

  function addTransaction(values: Entity) {
    const transaction = {
      id: nextId("txn"),
      occurred_at: new Date(2026, 5, 13, 12, state.transactions.length).toISOString(),
      actor: "qa",
      reason: null,
      ...values,
    };
    state.transactions.push(transaction);
    return transactionRead(transaction);
  }

  function dashboardSummary() {
    const inStock = state.bottles.filter((bottle) => bottle.current_status === "in_stock");
    const inStockReads = inStock.map(bottleRead);
    const occupiedByLocation = new Map<string, number>();
    for (const bottle of inStock) {
      if (bottle.current_location_id) {
        occupiedByLocation.set(bottle.current_location_id, (occupiedByLocation.get(bottle.current_location_id) ?? 0) + 1);
      }
    }
    const drinkWindowSummary = {
      UNKNOWN: 0,
      TOO_EARLY: 0,
      ENTERING: 0,
      IN_WINDOW: 0,
      LATE: 0,
      PAST: 0,
    };
    for (const bottle of inStockReads) {
      drinkWindowSummary[bottle.drink_window_status as keyof typeof drinkWindowSummary] += 1;
    }
    const insights = inStockReads.map((bottle) => ({
      bottle_id: bottle.id,
      bottle_label: `${bottle.producer_name ?? ""} · ${bottle.wine_name ?? "Wine"} · ${bottle.is_non_vintage ? "NV" : bottle.vintage_year}`,
      producer_name: bottle.producer_name,
      wine_name: bottle.wine_name,
      vintage_year: bottle.vintage_year,
      is_non_vintage: bottle.is_non_vintage,
      cellar_name: bottle.cellar_name,
      location_code: bottle.location_code,
      drink_from: bottle.default_drink_from,
      drink_to: bottle.default_drink_to,
      drink_window_status: bottle.drink_window_status,
      drink_window_confidence: bottle.drink_window_confidence,
      reason: bottle.drink_window_message,
    }));
    const knownWindowCount = inStockReads.length - drinkWindowSummary.UNKNOWN;
    const healthScore = inStockReads.length ? Math.round((knownWindowCount / inStockReads.length) * 35 + 35 + 20 + 10) : 60;
    return {
      total_bottles: state.bottles.length,
      in_stock_bottles: inStock.length,
      available_bottles: inStock.length,
      consumed_or_removed_bottles: state.bottles.length - inStock.length,
      unavailable_bottles: state.bottles.length - inStock.length,
      cellar_count: state.cellars.length,
      location_count: state.locations.length,
      recent_transactions: state.transactions.slice().reverse().slice(0, 8).map(transactionRead),
      status_counts: state.bottles.reduce<Record<string, number>>((acc, bottle) => {
        acc[bottle.current_status] = (acc[bottle.current_status] ?? 0) + 1;
        return acc;
      }, {}),
      drink_window_counts: { entering: inStock.length, past: 0, without: 0, future: 0 },
      drink_window_summary: drinkWindowSummary,
      upcoming_drink_candidates: insights.filter((item) => ["ENTERING", "IN_WINDOW"].includes(item.drink_window_status)),
      past_window_risks: insights.filter((item) => ["LATE", "PAST"].includes(item.drink_window_status)),
      inventory_by_country: inStock.length ? { France: inStock.length } : {},
      inventory_by_type: inStock.length ? { red: inStock.length } : {},
      cellar_occupancy: state.cellars.map((cellar) => {
        const locations = state.locations.filter((location) => location.cellar_id === cellar.id);
        const capacity = locations.reduce((sum, location) => sum + location.capacity, 0);
        const occupied = locations.reduce((sum, location) => sum + (occupiedByLocation.get(location.id) ?? 0), 0);
        return { cellar_id: cellar.id, name: cellar.name, capacity, occupied, empty: capacity - occupied };
      }),
      cellar_health_score: {
        score: healthScore,
        label: healthScore >= 85 ? "健康" : "需要关注",
        factors: [
          { key: "drink_window_coverage", label: "适饮期覆盖率", score: knownWindowCount ? 100 : 60, detail: `${knownWindowCount}/${inStockReads.length} 瓶在库酒有完整适饮期。` },
          { key: "overdue_risk", label: "过期风险", score: 100, detail: "0 瓶在库酒已晚于建议适饮期。" },
          { key: "occupancy_pressure", label: "酒柜容量压力", score: 100, detail: "测试酒柜容量正常。" },
          { key: "availability_balance", label: "可用库存平衡", score: 100, detail: `${inStock.length} 瓶可用。` },
        ],
        notes: ["测试环境使用本地 mock 评分。"],
      },
    };
  }

  async function fetch(input: RequestInfo | URL, init?: RequestInit) {
    const url = new URL(input.toString());
    const method = init?.method ?? "GET";
    const body = init?.body instanceof FormData ? init.body : init?.body ? JSON.parse(String(init.body)) : {};

    if (method === "GET" && url.pathname === "/api/dashboard/summary") return json(dashboardSummary());
    if (method === "GET" && url.pathname === "/api/producers") return json(state.producers);
    if (method === "GET" && url.pathname === "/api/wines") return json(state.wines);
    if (method === "GET" && url.pathname === "/api/vintages") return json(state.vintages);
    if (method === "GET" && url.pathname === "/api/cellars") return json(state.cellars);
    if (method === "GET" && url.pathname === "/api/locations") return json(state.locations.map(locationRead));
    if (method === "GET" && url.pathname === "/api/bottles") return json(state.bottles.map(bottleRead));
    if (method === "GET" && url.pathname === "/api/inventory-transactions") return json(state.transactions.map(transactionRead));

    if (method === "POST" && url.pathname === "/api/intake/label-images") {
      const uploadedFile = body instanceof FormData ? (body.get("file") as File | null) : null;
      const upload = {
        id: nextId("upload"),
        original_filename: uploadedFile?.name ?? "label.jpg",
        stored_filename: `upload-${id}.jpg`,
        content_type: uploadedFile?.type ?? "image/jpeg",
        size_bytes: uploadedFile?.size ?? 0,
        sha256: "a".repeat(64),
        file_path: "uploads/labels/upload.jpg",
        bottle_id: null,
        created_at: new Date(2026, 5, 13, 11, 0).toISOString(),
      };
      state.uploads.push(upload);
      return json(upload, 201);
    }

    if (method === "POST" && url.pathname === "/api/intake/label-drafts") {
      const upload = state.uploads.find((item) => item.id === body.upload_id);
      if (!upload) return json({ detail: "Label image upload not found" }, 404);
      return json({
        upload,
        recognizer: "mock-local-filename-heuristic",
        confidence: "low",
        candidate_fields: {
          producer_name: "Label Estate",
          wine_name: "Grand Vin",
          vintage_year: 2019,
          bottle_size_ml: 750,
          notes: `Draft generated from local filename: ${upload.original_filename}`,
        },
        warnings: ["Mock recognizer uses filename heuristics only; verify all fields before confirming."],
      });
    }

    if (method === "POST" && url.pathname === "/api/intake/label-drafts/confirm") {
      const upload = state.uploads.find((item) => item.id === body.upload_id);
      if (!upload) return json({ detail: "Label image upload not found" }, 404);
      let producer = state.producers.find((item) => item.name_original === body.producer_name);
      if (!producer) {
        producer = { id: nextId("producer"), name_original: body.producer_name, country: body.country ?? null };
        state.producers.push(producer);
      }
      let wine = state.wines.find((item) => item.producer_id === producer.id && item.name_original === body.wine_name);
      if (!wine) {
        wine = {
          id: nextId("wine"),
          producer_id: producer.id,
          name_original: body.wine_name,
          type: body.type ?? null,
          country: body.country ?? null,
          region: body.region ?? null,
        };
        state.wines.push(wine);
      }
      let vintage = state.vintages.find(
        (item) => item.wine_id === wine.id && item.vintage_year === body.vintage_year && !item.is_non_vintage,
      );
      if (!vintage) {
        vintage = { id: nextId("vintage"), wine_id: wine.id, vintage_year: body.vintage_year, is_non_vintage: false };
        state.vintages.push(vintage);
      }
      const bottle = {
        id: nextId("bottle"),
        vintage_id: vintage.id,
        current_status: "in_stock",
        current_location_id: body.location_id,
        bottle_size_ml: body.bottle_size_ml ?? 750,
        purchase_currency: "CNY",
        personal_notes: body.notes ?? null,
      };
      state.bottles.push(bottle);
      upload.bottle_id = bottle.id;
      addTransaction({
        bottle_id: bottle.id,
        transaction_type: "IN",
        from_location_id: null,
        to_location_id: body.location_id,
        note: `Label intake confirmed from upload ${upload.id}`,
      });
      return json({ bottle_id: bottle.id, upload_id: upload.id, transaction_type: "IN" }, 201);
    }

    if (method === "POST" && url.pathname === "/api/import/csv/draft") {
      return json({
        filename: body.filename ?? "qa.csv",
        required_fields: ["producer_name", "wine_name", "vintage_year", "bottle_size_ml", "cellar_name", "location_code"],
        optional_fields: ["country", "region", "type", "purchase_price"],
        total_rows: 2,
        valid_rows: 1,
        invalid_rows: 1,
        errors: [],
        rows: [
          {
            row_number: 2,
            status: "valid",
            raw: {
              producer_name: "Import Estate",
              wine_name: "Import Red",
              vintage_year: "2020",
              bottle_size_ml: "750",
              cellar_name: "QA柜",
              location_code: "A-01-01",
            },
            normalized: {
              producer_name: "Import Estate",
              wine_name: "Import Red",
              vintage_year: 2020,
              bottle_size_ml: 750,
              cellar_name: "QA柜",
              location_code: "A-01-01",
              purchase_currency: "CNY",
              tags: [],
            },
            errors: [],
            warnings: [],
          },
          {
            row_number: 3,
            status: "invalid",
            raw: { producer_name: "Broken Estate", wine_name: "", vintage_year: "bad" },
            normalized: null,
            errors: ["wine_name is required", "vintage_year must be an integer"],
            warnings: [],
          },
        ],
      });
    }

    if (method === "POST" && url.pathname === "/api/cellars") {
      const cellar = { id: nextId("cellar"), ...body };
      state.cellars.push(cellar);
      return json(cellar, 201);
    }
    const batchMatch = url.pathname.match(/^\/api\/cellars\/([^/]+)\/locations\/batch$/);
    if (method === "POST" && batchMatch) {
      const cellarId = batchMatch[1];
      for (let row = 1; row <= body.rows; row++) {
        for (let column = 1; column <= body.columns; column++) {
          state.locations.push({
            id: nextId("loc"),
            cellar_id: cellarId,
            code: `${body.code_prefix}-${String(row).padStart(2, "0")}-${String(column).padStart(2, "0")}`,
            row_index: row,
            column_index: column,
            capacity: body.capacity,
            location_type: "grid",
          });
        }
      }
      return json(state.locations.filter((location) => location.cellar_id === cellarId).map(locationRead), 201);
    }
    if (method === "POST" && url.pathname === "/api/producers") {
      const producer = { id: nextId("producer"), ...body };
      state.producers.push(producer);
      return json(producer, 201);
    }
    if (method === "POST" && url.pathname === "/api/wines") {
      const wine = { id: nextId("wine"), ...body };
      state.wines.push(wine);
      return json(wine, 201);
    }
    if (method === "POST" && url.pathname === "/api/vintages") {
      const vintage = { id: nextId("vintage"), ...body };
      state.vintages.push(vintage);
      return json(vintage, 201);
    }
    if (method === "POST" && url.pathname === "/api/bottles") {
      const bottle = {
        id: nextId("bottle"),
        current_status: "in_stock",
        lwin16: null,
        condition: null,
        purchase_channel: null,
        personal_rating: null,
        ...body,
      };
      state.bottles.push(bottle);
      addTransaction({
        bottle_id: bottle.id,
        transaction_type: "IN",
        from_location_id: null,
        to_location_id: bottle.current_location_id,
        note: body.note ?? null,
      });
      return json(bottleRead(bottle), 201);
    }
    if (method === "POST" && url.pathname === "/api/inventory-transactions") {
      const bottle = state.bottles.find((item) => item.id === body.bottle_id);
      if (!bottle) return json({ detail: "Bottle not found" }, 404);
      const fromLocationId = body.from_location_id ?? bottle.current_location_id ?? null;
      if (body.transaction_type === "MOVE") bottle.current_location_id = body.to_location_id;
      if (body.transaction_type === "CONSUME") {
        bottle.current_status = "drunk";
        bottle.current_location_id = null;
      }
      if (body.transaction_type === "ADJUST") {
        bottle.current_status = body.to_location_id ? "in_stock" : "lost";
        bottle.current_location_id = body.to_location_id ?? null;
      }
      return json(
        addTransaction({
          bottle_id: bottle.id,
          transaction_type: body.transaction_type,
          from_location_id: fromLocationId,
          to_location_id: body.to_location_id ?? null,
          note: body.note ?? null,
        }),
        201,
      );
    }

    return json({ detail: `${method} ${url.pathname} not mocked` }, 500);
  }

  return { fetch: vi.fn(fetch), state };
}

describe("Alpha UI smoke", () => {
  let server: ReturnType<typeof makeServer>;

  beforeEach(() => {
    server = makeServer();
    vi.stubGlobal("fetch", server.fetch);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("covers cellar, intake, MOVE, outbound, ADJUST, timeline, dashboard, grid, and CSV UI state", async () => {
    const user = userEvent.setup();
    const { container } = render(<App />);

    await screen.findByRole("heading", { name: "Dashboard" });
    expect(await screen.findByText("还没有入库记录。")).toBeTruthy();
    expect(screen.getByRole("link", { name: "导出 CSV" }).getAttribute("href")).toContain("/api/export/bottles.csv");

    await user.click(screen.getByRole("button", { name: "CSV 导入" }));
    const file = new File(
      [
        "producer_name,wine_name,vintage_year,bottle_size_ml,cellar_name,location_code\nImport Estate,Import Red,2020,750,QA柜,A-01-01",
      ],
      "qa.csv",
      { type: "text/csv" },
    );
    await user.upload(screen.getByLabelText("CSV 文件"), file);
    await user.click(screen.getByRole("button", { name: "解析草稿" }));
    await screen.findByText(/wine_name is required/);
    expect(screen.getByText("有效行")).toBeTruthy();
    expect(screen.getByText("错误行")).toBeTruthy();

    await user.click(screen.getByRole("button", { name: "酒柜地图" }));
    const managerForms = () => Array.from(container.querySelectorAll("form.mini-form")) as HTMLFormElement[];
    const createCellarForm = managerForms()[0];
    await user.type(within(createCellarForm).getByLabelText("名称"), "QA柜");
    await user.clear(within(createCellarForm).getByLabelText("行数"));
    await user.type(within(createCellarForm).getByLabelText("行数"), "2");
    await user.clear(within(createCellarForm).getByLabelText("列数"));
    await user.type(within(createCellarForm).getByLabelText("列数"), "3");
    await user.click(within(createCellarForm).getByRole("button", { name: "创建" }));
    await screen.findByText("酒柜已创建");

    const batchForm = managerForms()[2];
    await user.clear(within(batchForm).getByLabelText("行数"));
    await user.type(within(batchForm).getByLabelText("行数"), "2");
    await user.clear(within(batchForm).getByLabelText("列数"));
    await user.type(within(batchForm).getByLabelText("列数"), "3");
    await user.click(within(batchForm).getByRole("button", { name: "生成位置" }));
    await screen.findByText("位置已生成");
    expect(screen.getAllByText("A-01-01").length).toBeGreaterThan(0);
    expect(screen.getAllByText("空位").length).toBeGreaterThan(0);

    await user.click(screen.getByRole("button", { name: "酒标入库" }));
    const labelFile = new File([new Uint8Array([1, 2, 3])], "Label_Estate_Grand_Vin_2019_750ml.jpg", {
      type: "image/jpeg",
    });
    await user.upload(screen.getByLabelText("酒标图片"), labelFile);
    await user.click(screen.getByRole("button", { name: "生成草稿" }));
    await screen.findByDisplayValue("Label Estate");
    expect(screen.getByDisplayValue("Grand Vin")).toBeTruthy();
    expect(screen.getByDisplayValue("2019")).toBeTruthy();
    expect(screen.getByText(/Mock recognizer/)).toBeTruthy();

    await user.click(screen.getByRole("button", { name: "新增入库" }));
    await user.type(screen.getByLabelText("新酒庄英文/原名"), "QA Estate");
    await user.type(screen.getByLabelText("新酒庄中文名"), "QA酒庄");
    await user.type(screen.getByLabelText("酒庄国家"), "France");
    await user.type(screen.getByLabelText("新酒款英文/原名"), "QA Grand Vin");
    await user.type(screen.getByLabelText("新酒款中文名"), "QA正牌");
    await user.type(screen.getByLabelText("酒款国家"), "France");
    await user.clear(screen.getByLabelText("新年份"));
    await user.type(screen.getByLabelText("新年份"), "2020");
    await user.type(screen.getByLabelText("适饮开始年"), "2025");
    await user.type(screen.getByLabelText("适饮结束年"), "2028");
    await user.selectOptions(screen.getByLabelText("适饮置信度"), "low");
    await user.selectOptions(screen.getByLabelText("选择酒柜"), server.state.cellars[0].id);
    await user.selectOptions(screen.getByLabelText("选择位置"), server.state.locations[0].id);
    await user.type(screen.getByLabelText("购入日期"), "2026-06-13");
    await user.type(screen.getByLabelText("购买价"), "188.00");
    await user.type(screen.getByLabelText("购买来源"), "QA来源");
    await user.type(screen.getByLabelText("备注"), "UI smoke");
    await user.click(screen.getByRole("button", { name: "确认入库" }));

    await screen.findByRole("heading", { name: "QA酒庄 · QA正牌 · 2020" });
    expect(screen.getByText("QA柜 / A-01-01")).toBeTruthy();
    expect(screen.getByText("2025-2028")).toBeTruthy();
    expect(screen.getByText("CNY 188.00")).toBeTruthy();
    expect(screen.getByText("入库")).toBeTruthy();

    const actionPanel = () => container.querySelector("form.action-panel") as HTMLFormElement;
    await user.selectOptions(within(actionPanel()).getByLabelText("目标位置"), server.state.locations[1].id);
    await user.type(within(actionPanel()).getByLabelText("备注"), "移动到第二格");
    await user.click(within(actionPanel()).getByRole("button", { name: "确认移动" }));
    await screen.findByText("移动已记录");
    expect(screen.getByText("QA柜 / A-01-02")).toBeTruthy();
    expect(screen.getByText("从 A-01-01 / 到 A-01-02")).toBeTruthy();

    await user.click(screen.getByRole("button", { name: "酒柜地图" }));
    expect(screen.getByText("占用 1/1")).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "QA正牌" }));
    await screen.findByRole("heading", { name: "QA酒庄 · QA正牌 · 2020" });

    await user.click(within(actionPanel()).getByRole("button", { name: "饮用" }));
    await user.type(within(actionPanel()).getByLabelText("备注"), "QA出库");
    await user.click(within(actionPanel()).getByRole("button", { name: "确认饮用" }));
    await screen.findByText("饮用已记录");
    expect(screen.getByText("已饮用")).toBeTruthy();
    expect(screen.getByText("无位置")).toBeTruthy();
    expect((within(actionPanel()).getByRole("button", { name: "移动" }) as HTMLButtonElement).disabled).toBe(true);
    expect((within(actionPanel()).getByRole("button", { name: "饮用" }) as HTMLButtonElement).disabled).toBe(true);

    await user.selectOptions(within(actionPanel()).getByLabelText("调整后位置（留空则标记盘亏）"), server.state.locations[2].id);
    await user.type(within(actionPanel()).getByLabelText("备注（必填）"), "盘点纠正回库");
    await user.click(within(actionPanel()).getByRole("button", { name: "确认盘点调整" }));
    await screen.findByText("盘点调整已记录");
    expect(screen.getByText("QA柜 / A-01-03")).toBeTruthy();
    expect(screen.getAllByText("盘点调整").length).toBeGreaterThan(0);

    await user.click(screen.getByRole("button", { name: "Dashboard" }));
    await waitFor(() => expect(screen.getAllByText("酒窖健康").length).toBeGreaterThan(0));
    expect(screen.getByText("适饮状态")).toBeTruthy();
    expect(screen.getByText("1/6 已占用，5 空位")).toBeTruthy();
  }, 15000);
});
