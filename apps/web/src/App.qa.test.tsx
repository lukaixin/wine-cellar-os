import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
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

  function collectionSearch(url: URL) {
    const query = (url.searchParams.get("q") ?? "").trim().toLocaleLowerCase();
    const producerId = url.searchParams.get("producer_id") ?? "";
    const vintageYear = url.searchParams.get("vintage_year") ?? "";
    const locationId = url.searchParams.get("location_id") ?? "";
    const status = url.searchParams.get("status") ?? "";
    const limit = Number(url.searchParams.get("limit") ?? 25);
    const offset = Number(url.searchParams.get("offset") ?? 0);
    const filtered = state.bottles.filter((bottle) => {
      const read = bottleRead(bottle);
      const haystack = [
        read.producer_name,
        read.producer_name_cn,
        read.wine_name,
        read.wine_name_cn,
        read.vintage_year,
        read.is_non_vintage ? "NV" : "",
      ].filter(Boolean).join(" ").toLocaleLowerCase();
      const producer = state.producers.find((item) => item.name_original === read.producer_name);
      if (query && !haystack.includes(query)) return false;
      if (producerId && producer?.id !== producerId) return false;
      if (vintageYear && String(read.vintage_year ?? "") !== vintageYear) return false;
      if (locationId && bottle.current_location_id !== locationId) return false;
      if (status && bottle.current_status !== status) return false;
      return true;
    });
    const groups = new Map<string, Entity[]>();
    for (const bottle of filtered) {
      groups.set(`${bottle.vintage_id}:${bottle.current_location_id ?? ""}:${bottle.current_status}`, [
        ...(groups.get(`${bottle.vintage_id}:${bottle.current_location_id ?? ""}:${bottle.current_status}`) ?? []),
        bottle,
      ]);
    }
    const items = Array.from(groups.values()).map((group) => {
      const first = bottleRead(group[0]);
      const wine = state.wines.find((item) => item.name_original === first.wine_name);
      const producer = state.producers.find((item) => item.name_original === first.producer_name);
      return {
        bottle_id: first.id,
        bottle_ids: group.map((item) => item.id),
        producer_id: producer?.id ?? null,
        producer_name: first.producer_name,
        producer_name_cn: first.producer_name_cn,
        wine_id: wine?.id ?? null,
        wine_name: first.wine_name,
        wine_name_cn: first.wine_name_cn,
        vintage_id: first.vintage_id,
        vintage_year: first.vintage_year,
        is_non_vintage: first.is_non_vintage,
        bottle_count: group.length,
        location: {
          id: first.current_location_id,
          cellar_name: first.cellar_name,
          code: first.location_code,
        },
        status: first.current_status,
      };
    });
    return {
      query: query || null,
      total: items.length,
      limit,
      offset,
      items: items.slice(offset, offset + limit),
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

  function applyInventoryAction(transactionType: "CONSUME" | "GIFT" | "DAMAGE" | "MOVE", body: Entity) {
    const bottle = state.bottles.find((item) => item.id === body.bottle_id);
    if (!bottle) return json({ detail: "Bottle not found" }, 404);
    if (bottle.current_status !== "in_stock") {
      return json({ detail: `Cannot create ${transactionType}: bottle is already unavailable with status ${bottle.current_status}` }, 409);
    }
    if (transactionType !== "MOVE" && body.quantity !== 1) {
      return json({ detail: "quantity must be 1 because each Bottle record represents one physical bottle" }, 422);
    }
    const fromLocationId = transactionType === "MOVE" ? body.from_location : bottle.current_location_id ?? null;
    if (transactionType === "MOVE") {
      if (fromLocationId !== bottle.current_location_id) return json({ detail: "from_location_id must match bottle current_location_id" }, 409);
      if (!state.locations.some((location) => location.id === body.to_location)) return json({ detail: "Location not found" }, 404);
      bottle.current_location_id = body.to_location;
    }
    if (transactionType === "CONSUME") {
      bottle.current_status = "drunk";
      bottle.current_location_id = null;
    }
    if (transactionType === "GIFT") {
      bottle.current_status = "gifted";
      bottle.current_location_id = null;
    }
    if (transactionType === "DAMAGE") {
      bottle.current_status = "damaged";
      bottle.current_location_id = null;
    }
    return json(
      addTransaction({
        bottle_id: bottle.id,
        transaction_type: transactionType,
        from_location_id: fromLocationId,
        to_location_id: transactionType === "MOVE" ? body.to_location : null,
        reason: transactionType === "GIFT" ? `Recipient: ${body.recipient}` : transactionType === "DAMAGE" ? body.reason : null,
        note: body.notes ?? null,
      }),
      201,
    );
  }

  const importBatchDetail = {
    id: "batch-1",
    filename: "WineList.xlsx",
    sheet_name: "Stock",
    file_sha256: "b".repeat(64),
    status: "confirmed",
    created_at: new Date(2026, 5, 13, 9, 0).toISOString(),
    confirmed_at: new Date(2026, 5, 13, 9, 5).toISOString(),
    total_rows: 114,
    success_rows: 114,
    warning_rows: 1,
    error_rows: 1,
    created_bottle_count: 119,
    warnings: ["Region normalized from Sorthern Rhone to Southern Rhone"],
    rows: [
      {
        row_number: 2,
        raw_values: { Producer: "Sample Estate", Wine: "Sample Wine", Vintage: "2020", Quantity: "2" },
        parsed_producer: "Sample Estate",
        parsed_wine: "Sample Wine",
        parsed_vintage: 2020,
        quantity: 2,
        warnings: ["Cost is blank; purchase_price will be null"],
        errors: [],
        created_bottle_ids: ["bottle-winelist-1", "bottle-winelist-2"],
        ledger_transaction_ids: ["txn-winelist-1", "txn-winelist-2"],
      },
      {
        row_number: 3,
        raw_values: { Producer: "Broken Estate", Wine: "", Vintage: "bad", Quantity: "1" },
        parsed_producer: null,
        parsed_wine: null,
        parsed_vintage: null,
        quantity: null,
        warnings: [],
        errors: ["Vintage must be a year: bad"],
        created_bottle_ids: [],
        ledger_transaction_ids: [],
      },
    ],
  };
  const registryFindings = [
    {
      id: "finding-1",
      finding_type: "missing_region",
      severity: "low",
      entity_type: "producer",
      entity_id: "producer-qa",
      evidence: { producer: "QA Estate" },
      evidence_hash: "f".repeat(64),
      suggested_action: "补充产区，无法确认时保持 manual/low confidence。",
      status: "open",
      created_at: new Date(2026, 5, 13, 9, 15).toISOString(),
    },
  ];
  const registryReviewQueue = [
    {
      id: "review-1",
      review_type: "match_range",
      status: "open",
      source: "winelist:Stock",
      entity_type: "producer",
      entity_id: "producer-qa",
      import_mapping_id: "mapping-1",
      raw_value: { field: "Producer", value: "Sample Est." },
      match_score: 88,
      title: "WineList row 2 needs registry review",
      detail: "Producer matched at 88; review before treating it as stable.",
      evidence: { candidate_key: "sample estate" },
      created_at: new Date(2026, 5, 13, 9, 16).toISOString(),
    },
  ];
  const registryAliases = [
    {
      id: "alias-1",
      entity_type: "producer",
      entity_id: "producer-qa",
      alias_text: "Sample Est.",
      alias_key: "sample est",
      status: "candidate",
      source: "winelist:Stock",
      rule_version: "registry-v1",
      confidence: "low",
      import_mapping_id: "mapping-1",
      reviewed_at: null,
      note: null,
      created_at: new Date(2026, 5, 13, 9, 17).toISOString(),
      updated_at: new Date(2026, 5, 13, 9, 17).toISOString(),
    },
  ];
  const registryImportMappings = [
    {
      id: "mapping-1",
      source: "winelist:Stock",
      import_batch_id: "batch-1",
      import_batch_row_id: "row-1",
      source_row_number: 2,
      raw_value: { field: "Producer", value: "Sample Est." },
      target_entity_type: "producer",
      target_entity_id: "producer-qa",
      match_score: 88,
      decision: "needs_review",
      rule_version: "registry-v1",
      evidence: { matched_by: "fuzzy_key" },
      created_at: new Date(2026, 5, 13, 9, 18).toISOString(),
    },
  ];
  const registrySearch = {
    query: "drc",
    producers: [
      {
        id: "producer-drc",
        entity_type: "producer",
        display_name: "Domaine de la Romanee-Conti",
        matched_text: "DRC",
        matched_by: "alias",
        score: 96,
        quality_status: "approved",
      },
    ],
    wines: [
      {
        id: "wine-rc",
        entity_type: "wine",
        display_name: "Domaine de la Romanee-Conti · Romanee-Conti Grand Cru",
        matched_text: "罗曼尼康帝",
        matched_by: "chinese_name",
        score: 92,
        quality_status: "unreviewed",
      },
    ],
    vintages: [
      {
        id: "vintage-rc",
        entity_type: "vintage",
        display_name: "Domaine de la Romanee-Conti · Romanee-Conti Grand Cru · 2020",
        matched_text: "Romanee Conti",
        matched_by: "fuzzy",
        score: 88,
        quality_status: "unreviewed",
      },
    ],
  };
  const registryDiscovery = {
    recent_producers: [
      {
        id: "producer-drc",
        entity_type: "producer",
        display_name: "Domaine de la Romanee-Conti",
        created_at: new Date(2026, 5, 13, 9, 20).toISOString(),
        quality_status: "approved",
      },
    ],
    recent_wines: [
      {
        id: "wine-rc",
        entity_type: "wine",
        display_name: "Domaine de la Romanee-Conti · Romanee-Conti Grand Cru",
        created_at: new Date(2026, 5, 13, 9, 21).toISOString(),
        quality_status: "unreviewed",
      },
    ],
    recent_vintages: [
      {
        id: "vintage-rc",
        entity_type: "vintage",
        display_name: "Domaine de la Romanee-Conti · Romanee-Conti Grand Cru · 2020",
        created_at: new Date(2026, 5, 13, 9, 22).toISOString(),
        quality_status: "unreviewed",
      },
    ],
    quality_risks: [
      {
        id: "risk-1",
        finding_type: "duplicate_producer",
        severity: "high",
        entity_type: "producer",
        entity_id: "producer-drc",
        suggested_action: "人工确认是否需要设置 merged_into_id；不要自动合并历史数据。",
        evidence: { canonical_key: "domaine de la romanee conti" },
        created_at: new Date(2026, 5, 13, 9, 23).toISOString(),
      },
    ],
  };
  const registryDetails: Record<string, Entity> = {
    "/registry/producers/producer-drc": {
      id: "producer-drc",
      entity_type: "producer",
      canonical_name: "Domaine de la Romanee-Conti",
      name_cn: "罗曼尼康帝",
      aliases: ["DRC"],
      country: "France",
      region: "Bourgogne",
      wine_count: 1,
      quality_status: "approved",
      canonical_key: "domaine de la romanee conti",
    },
    "/registry/wines/wine-rc": {
      id: "wine-rc",
      entity_type: "wine",
      canonical_name: "Romanee-Conti Grand Cru",
      name_cn: "罗曼尼康帝特级园",
      producer_id: "producer-drc",
      producer_name: "Domaine de la Romanee-Conti",
      aliases: ["Romanee Conti"],
      vintage_count: 1,
      quality_status: "unreviewed",
      wine_identity_key: "domaine de la romanee conti | romanee conti grand cru | france | bourgogne | red",
    },
    "/registry/vintages/vintage-rc": {
      id: "vintage-rc",
      entity_type: "vintage",
      producer_id: "producer-drc",
      producer_name: "Domaine de la Romanee-Conti",
      wine_id: "wine-rc",
      wine_name: "Romanee-Conti Grand Cru",
      vintage_year: 2020,
      is_non_vintage: false,
      bottle_count: 2,
      default_drink_from: 2030,
      default_drink_to: 2050,
      drink_window_confidence: "low",
      drink_windows: [
        {
          source: "manual",
          source_detail: "QA",
          drink_from: 2030,
          drink_to: 2050,
          peak_from: null,
          peak_to: null,
          confidence: "low",
          notes: "人工录入",
        },
      ],
      quality_status: "unreviewed",
    },
  };

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
    if (method === "GET" && url.pathname === "/collection/search") return json(collectionSearch(url));
    const collectionBottleMatch = url.pathname.match(/^\/collection\/bottles\/([^/]+)$/);
    if (method === "GET" && collectionBottleMatch) {
      const bottle = state.bottles.find((item) => item.id === collectionBottleMatch[1]);
      if (!bottle) return json({ detail: "Bottle not found" }, 404);
      const read = bottleRead(bottle);
      const wine = state.wines.find((item) => item.name_original === read.wine_name);
      const producer = state.producers.find((item) => item.name_original === read.producer_name);
      return json({
        id: read.id,
        bottle_id: read.id,
        bottle_size_ml: read.bottle_size_ml,
        quantity: 1,
        status: read.current_status,
        acquisition_date: read.acquisition_date ?? null,
        vintage_id: read.vintage_id,
        vintage_year: read.vintage_year,
        is_non_vintage: read.is_non_vintage,
        wine_id: wine?.id ?? null,
        wine_name: read.wine_name,
        wine_name_cn: read.wine_name_cn,
        producer_id: producer?.id ?? null,
        producer_name: read.producer_name,
        producer_name_cn: read.producer_name_cn,
        location: {
          id: read.current_location_id,
          cellar_name: read.cellar_name,
          code: read.location_code,
        },
        created_at: read.created_at ?? new Date(2026, 5, 13, 12, 0).toISOString(),
        updated_at: read.updated_at ?? new Date(2026, 5, 13, 12, 0).toISOString(),
      });
    }
    const collectionTimelineMatch = url.pathname.match(/^\/collection\/bottles\/([^/]+)\/timeline$/);
    if (method === "GET" && collectionTimelineMatch) {
      const bottle = state.bottles.find((item) => item.id === collectionTimelineMatch[1]);
      if (!bottle) return json({ detail: "Bottle not found" }, 404);
      const events = state.transactions
        .filter((transaction) => transaction.bottle_id === bottle.id)
        .slice()
        .sort((a, b) => String(b.occurred_at).localeCompare(String(a.occurred_at)))
        .map((transaction) => {
          const from = state.locations.find((item) => item.id === transaction.from_location_id);
          const to = state.locations.find((item) => item.id === transaction.to_location_id);
          const fromCellar = state.cellars.find((item) => item.id === from?.cellar_id);
          const toCellar = state.cellars.find((item) => item.id === to?.cellar_id);
          return {
            event_type: transaction.transaction_type,
            event_time: transaction.occurred_at,
            quantity_delta: transaction.transaction_type === "IN" ? 1 : ["CONSUME", "GIFT", "DAMAGE"].includes(transaction.transaction_type) ? -1 : 0,
            reference_type: "inventory_transaction",
            reference_id: transaction.id,
            from_location: from ? { id: from.id, cellar_name: fromCellar?.name ?? null, code: from.code } : { id: null, cellar_name: null, code: null },
            to_location: to ? { id: to.id, cellar_name: toCellar?.name ?? null, code: to.code } : { id: null, cellar_name: null, code: null },
            notes: transaction.note ?? transaction.reason ?? null,
          };
        });
      return json(events);
    }
    if (method === "GET" && url.pathname === "/api/inventory-transactions") return json(state.transactions.map(transactionRead));
    if (method === "GET" && url.pathname === "/imports/batches") {
      return json({
        total: 1,
        limit: Number(url.searchParams.get("limit") ?? 50),
        offset: Number(url.searchParams.get("offset") ?? 0),
        items: [
          {
            id: importBatchDetail.id,
            filename: importBatchDetail.filename,
            status: importBatchDetail.status,
            created_at: importBatchDetail.created_at,
            confirmed_at: importBatchDetail.confirmed_at,
            total_rows: importBatchDetail.total_rows,
            success_rows: importBatchDetail.success_rows,
            warning_rows: importBatchDetail.warning_rows,
            error_rows: importBatchDetail.error_rows,
            created_bottle_count: importBatchDetail.created_bottle_count,
          },
        ],
      });
    }
    if (method === "GET" && url.pathname === "/imports/batches/batch-1") return json(importBatchDetail);
    if (method === "GET" && url.pathname === "/registry/quality/findings") return json(registryFindings);
    if (method === "GET" && url.pathname === "/registry/review-queue") return json(registryReviewQueue);
    if (method === "GET" && url.pathname === "/registry/aliases") return json(registryAliases);
    if (method === "GET" && url.pathname === "/registry/import-mappings") return json(registryImportMappings);
    if (method === "GET" && url.pathname === "/registry/search") return json({ ...registrySearch, query: url.searchParams.get("q") ?? "" });
    if (method === "GET" && url.pathname === "/registry/discovery") return json(registryDiscovery);
    if (method === "GET" && registryDetails[url.pathname]) return json(registryDetails[url.pathname]);

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

    if (method === "POST" && url.pathname === "/api/import/winelist/draft") {
      return json({
        batch_id: "batch-1",
        filename: "WineList.xlsx",
        sheet_name: "Stock",
        file_sha256: "b".repeat(64),
        total_rows: 114,
        valid_rows: 114,
        invalid_rows: 0,
        bottle_count: 119,
        location_counts: {
          "法国朋友家 / FR": 3,
          "家中酒柜 / C": 86,
          "家中散放 / HOME-OUTSIDE": 30,
        },
        registry_preview: {
          producers_new: 80,
          producers_existing: 0,
          wines_new: 100,
          wines_existing: 0,
          vintages_new: 110,
          vintages_existing: 0,
        },
        warnings: ["Region normalized from Sorthern Rhone to Southern Rhone"],
        rows: [
          {
            id: "row-1",
            row_number: 2,
            status: "valid",
            raw: { Producer: "Sample Estate", Wine: "Sample Wine", Vintage: "2020", Quantity: "2" },
            normalized: {
              country: "France",
              region: "Southern Rhone",
              appellation: "Cote Rotie",
              producer_name: "Sample Estate",
              wine_name: "Sample Wine",
              type: "red",
              vintage_year: 2020,
              quantity: 2,
              bottle_size_ml: 750,
              purchase_price: "288.00",
              purchase_currency: "CNY",
              purchase_channel: "merchant",
              purchase_source: "WineList.xlsx Stock",
              cellar_name: "家中酒柜",
              location_code: "C",
              location_label: "家中酒柜 / C",
              location_key: "CAVE_C",
              producer_match_score: 100,
              wine_match_score: 100,
              vintage_match_score: 100,
              overall_match_score: 100,
              decision: "auto_accepted",
            },
            errors: [],
            warnings: [],
            bottle_count: 2,
          },
        ],
      });
    }

    if (method === "POST" && url.pathname === "/api/import/winelist/batch-1/confirm") {
      return json({
        batch_id: "batch-1",
        created_bottles: 119,
        created_bottle_ids: ["bottle-winelist-1"],
        created_transaction_ids: ["txn-winelist-1"],
        location_counts: {
          "法国朋友家 / FR": 3,
          "家中酒柜 / C": 86,
          "家中散放 / HOME-OUTSIDE": 30,
        },
        transaction_type: "IN",
        warnings: [],
      }, 201);
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
    if (method === "POST" && url.pathname === "/inventory/actions/consume") {
      return applyInventoryAction("CONSUME", body);
    }
    if (method === "POST" && url.pathname === "/inventory/actions/gift") {
      return applyInventoryAction("GIFT", body);
    }
    if (method === "POST" && url.pathname === "/inventory/actions/damage") {
      return applyInventoryAction("DAMAGE", body);
    }
    if (method === "POST" && url.pathname === "/inventory/actions/move") {
      return applyInventoryAction("MOVE", body);
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
    cleanup();
    vi.unstubAllGlobals();
  });

  it("covers cellar, intake, MOVE, outbound, ADJUST, timeline, dashboard, grid, and CSV UI state", async () => {
    const user = userEvent.setup();
    const { container } = render(<App />);

    await screen.findByRole("heading", { name: "Dashboard" });
    expect(await screen.findByText("还没有入库记录。")).toBeTruthy();
    expect(screen.getByRole("link", { name: "导出 CSV" }).getAttribute("href")).toContain("/api/export/bottles.csv");

    await user.click(screen.getByRole("button", { name: "库存导入" }));
    const wineListFile = new File([new Uint8Array([1, 2, 3])], "WineList.xlsx", {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
    await user.upload(screen.getByLabelText("WineList.xlsx 文件"), wineListFile);
    await user.click(screen.getByRole("button", { name: "解析 WineList" }));
    await screen.findByText("WineList dry-run 结果");
    expect(screen.getByText("展开瓶数")).toBeTruthy();
    expect(screen.getByText("法国朋友家 / FR")).toBeTruthy();
    await screen.findByText("Import Batch History");
    await user.click(screen.getAllByRole("button", { name: "查看" })[0]);
    await screen.findByText("Import Batch Detail");
    expect(screen.getAllByText("Region normalized from Sorthern Rhone to Southern Rhone").length).toBeGreaterThan(0);
    expect(screen.getByText("Cost is blank; purchase_price will be null")).toBeTruthy();
    expect(screen.getByText("Vintage must be a year: bad")).toBeTruthy();
    expect(screen.getByText(/bottle-winelist-1/)).toBeTruthy();
    expect(screen.getByText(/txn-winelist-1/)).toBeTruthy();

    await user.click(screen.getByRole("button", { name: "Registry Quality" }));
    await waitFor(() => expect(screen.getAllByText("Findings").length).toBeGreaterThan(0));
    expect(screen.getAllByText("Review Queue").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Alias").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Import Mapping").length).toBeGreaterThan(0);
    expect(screen.getByText("missing_region")).toBeTruthy();
    expect(screen.getByText("needs_review")).toBeTruthy();

    await user.click(screen.getByRole("button", { name: "Registry Search" }));
    await screen.findByText("Discovery");
    expect(screen.getAllByText("Domaine de la Romanee-Conti").length).toBeGreaterThan(0);
    expect(screen.getByText("duplicate_producer")).toBeTruthy();
    await user.type(screen.getByLabelText("Registry 查询"), "drc");
    await user.click(screen.getByRole("button", { name: "搜索" }));
    await screen.findByText("Search Results");
    expect(screen.getByText("Producer Results")).toBeTruthy();
    expect(screen.getByText("Vintage Results")).toBeTruthy();
    expect(screen.getByText("Alias")).toBeTruthy();
    expect(screen.getByText("Fuzzy")).toBeTruthy();
    await user.click(screen.getAllByText("Domaine de la Romanee-Conti")[0]);
    await screen.findByText("Wine Count");
    expect(screen.getByText("Bourgogne")).toBeTruthy();
    expect(screen.getAllByText("DRC").length).toBeGreaterThan(0);

    await user.click(screen.getByRole("button", { name: "库存导入" }));

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
    expect(screen.getAllByText("有效行").length).toBeGreaterThan(0);
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

    await user.click(screen.getByRole("button", { name: "Collection Explorer" }));
    await screen.findByText("Result List");
    await user.type(screen.getByLabelText("Collection Search"), "QA");
    await user.selectOptions(screen.getByLabelText("Location"), server.state.locations[1].id);
    await user.selectOptions(screen.getByLabelText("Status"), "in_stock");
    await user.click(screen.getByRole("button", { name: "搜索" }));
    await screen.findByText("QA正牌");
    expect(screen.getAllByText("QA柜 / A-01-02").length).toBeGreaterThan(0);
    expect(screen.getAllByText("在库").length).toBeGreaterThan(0);
    await user.click(screen.getByRole("button", { name: /展开 1 Bottles/ }));
    await screen.findByRole("button", { name: /Bottle #1/ });
    await user.click(screen.getByRole("button", { name: /Bottle #1/ }));
    await screen.findByText("Bottle Size");
    expect(screen.getByText("Acquisition Date")).toBeTruthy();
    expect(screen.getAllByText("2026-06-13").length).toBeGreaterThan(0);
    await user.click(screen.getByRole("button", { name: "Timeline" }));
    await screen.findByText("移动到第二格");
    expect(screen.getAllByText("移动").length).toBeGreaterThan(0);

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

  it("submits Collection Explorer actions and refreshes the timeline", async () => {
    const user = userEvent.setup();
    server.state.cellars.push({ id: "cellar-action", name: "Action柜", cellar_type: "cabinet" });
    server.state.locations.push(
      { id: "loc-action-1", cellar_id: "cellar-action", code: "A-01-01", capacity: 2, location_type: "grid" },
      { id: "loc-action-2", cellar_id: "cellar-action", code: "A-01-02", capacity: 2, location_type: "grid" },
    );
    server.state.producers.push({ id: "producer-action", name_original: "Action Estate", name_cn: "行动酒庄" });
    server.state.wines.push({
      id: "wine-action",
      producer_id: "producer-action",
      name_original: "Action Red",
      name_cn: "行动红",
      type: "red",
      country: "France",
    });
    server.state.vintages.push({ id: "vintage-action", wine_id: "wine-action", vintage_year: 2020, is_non_vintage: false });
    server.state.bottles.push({
      id: "bottle-action",
      vintage_id: "vintage-action",
      current_status: "in_stock",
      current_location_id: "loc-action-1",
      bottle_size_ml: 750,
      acquisition_date: "2026-06-14",
      purchase_currency: "CNY",
    });
    server.state.transactions.push({
      id: "txn-action-in",
      bottle_id: "bottle-action",
      transaction_type: "IN",
      from_location_id: null,
      to_location_id: "loc-action-1",
      occurred_at: new Date(2026, 5, 14, 8, 0).toISOString(),
      actor: "qa",
      reason: null,
      note: "seed",
    });

    render(<App />);

    await screen.findByRole("heading", { name: "Dashboard" });
    await user.click(screen.getByRole("button", { name: "Collection Explorer" }));
    await screen.findByText("Result List");
    await user.type(screen.getByLabelText("Collection Search"), "Action");
    await user.click(screen.getByRole("button", { name: "搜索" }));
    await screen.findByText("行动红");
    await user.click(screen.getByRole("button", { name: /展开 1 Bottles/ }));
    await user.click(screen.getByRole("button", { name: /Bottle #1/ }));
    await screen.findByText("Bottle Size");

    await user.click(screen.getByRole("button", { name: "Actions" }));
    await user.clear(screen.getByLabelText("Quantity"));
    await user.type(screen.getByLabelText("Quantity"), "2");
    await user.type(screen.getByLabelText("Notes"), "Weekend dinner");
    await user.click(screen.getByRole("button", { name: "确认饮用" }));
    await screen.findByText("单瓶操作数量必须为 1。");

    await user.clear(screen.getByLabelText("Quantity"));
    await user.type(screen.getByLabelText("Quantity"), "1");
    await user.click(screen.getByRole("button", { name: "确认饮用" }));

    await screen.findByText("饮用已记录");
    await screen.findByText("Weekend dinner");
    expect(screen.getAllByText("已饮用").length).toBeGreaterThan(0);
    expect(screen.getAllByText("饮用").length).toBeGreaterThan(0);
  }, 10000);
});
