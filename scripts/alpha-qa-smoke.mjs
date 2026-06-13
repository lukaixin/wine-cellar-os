import { existsSync, rmSync } from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const rootDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const apiDir = path.join(rootDir, "apps", "api");
const dbFile = path.join(apiDir, ".alpha-qa-smoke.db");
const dataDir = path.join(apiDir, ".alpha-qa-data");
const port = Number(process.env.ALPHA_QA_API_PORT ?? 18000);
const base = `http://127.0.0.1:${port}`;
const python = process.env.WINE_CELLAR_PYTHON ?? process.env.PYTHON ?? "python";

function removeGeneratedPath(target, options = {}) {
  const resolved = path.resolve(target);
  const relative = path.relative(rootDir, resolved);
  if (relative.startsWith("..") || path.isAbsolute(relative)) {
    throw new Error(`Refusing to remove generated path outside workspace: ${resolved}`);
  }
  if (existsSync(resolved)) rmSync(resolved, { force: true, ...options });
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForApi(process) {
  for (let attempt = 0; attempt < 40; attempt++) {
    if (process.exitCode !== null) break;
    try {
      const response = await fetch(`${base}/health`);
      if (response.ok) return;
    } catch {
      // Keep polling until the server is ready or the process exits.
    }
    await sleep(250);
  }
  throw new Error(`API did not become ready at ${base}`);
}

async function req(method, path, body) {
  const response = await fetch(base + path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await response.text();
  let data;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  return { status: response.status, body: data, text };
}

async function uploadFile(path, filename, contentType, bytes) {
  const form = new FormData();
  form.append("file", new Blob([bytes], { type: contentType }), filename);
  const response = await fetch(base + path, {
    method: "POST",
    body: form,
  });
  const text = await response.text();
  let data;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  return { status: response.status, body: data, text };
}

function check(name, condition, detail, failures) {
  if (!condition) failures.push({ name, detail });
}

async function runSmoke() {
  const failures = [];

  const cellar = await req("POST", "/api/cellars", { name: "QA柜", cellar_type: "cabinet", rows: 2, columns: 5 });
  check("create cellar", cellar.status === 201, cellar, failures);
  const cellarId = cellar.body.id;

  const batch = await req("POST", `/api/cellars/${cellarId}/locations/batch`, {
    rows: 2,
    columns: 5,
    code_prefix: "Q",
    capacity: 1,
  });
  check("batch create locations", batch.status === 201 && batch.body.length === 10, batch, failures);
  const locations = batch.body;

  const producer = await req("POST", "/api/producers", {
    name_original: "QA Estate",
    name_cn: "QA酒庄",
    country: "France",
  });
  check("create producer", producer.status === 201, producer, failures);

  const wine = await req("POST", "/api/wines", {
    producer_id: producer.body.id,
    name_original: "QA Grand Vin",
    name_cn: "QA正牌",
    type: "red",
    country: "France",
  });
  check("create wine", wine.status === 201, wine, failures);

  const vintage = await req("POST", "/api/vintages", {
    wine_id: wine.body.id,
    vintage_year: 2020,
    is_non_vintage: false,
    default_drink_from: 2025,
    default_drink_to: 2028,
    drink_window_confidence: "low",
  });
  check("create vintage", vintage.status === 201, vintage, failures);

  async function bottleAt(locationIndex, note) {
    const bottle = await req("POST", "/api/bottles", {
      vintage_id: vintage.body.id,
      current_location_id: locations[locationIndex].id,
      purchase_price: "188.00",
      purchase_currency: "CNY",
      purchase_source: "QA",
      personal_notes: note,
      note: "QA入库",
    });
    check(`add bottle ${note}`, bottle.status === 201, bottle, failures);
    return bottle.body;
  }

  const bConsume = await bottleAt(0, "consume-flow");
  const bGift = await bottleAt(2, "gift-flow");
  const bDamage = await bottleAt(3, "damage-flow");
  const bAdjust = await bottleAt(4, "adjust-flow");

  const importCsvText = [
    "producer_name,wine_name,vintage_year,bottle_size_ml,cellar_name,location_code,country,region,type,purchase_price,purchase_currency,purchase_date,purchase_source,drink_from,drink_to,notes",
    "QA Import Estate,QA Import Red,2021,750,QA柜,Q-02-02,France,Bordeaux,red,268.00,CNY,2026-06-13,QA Importer,2025,2030,qa import",
  ].join("\n");
  const importDraft = await req("POST", "/api/import/csv/draft", {
    filename: "qa-import.csv",
    csv_text: importCsvText,
  });
  check("csv import draft", importDraft.status === 200 && importDraft.body.valid_rows === 1, importDraft, failures);
  const importConfirm = await req("POST", "/api/import/csv/confirm", {
    rows: [importDraft.body.rows[0].normalized],
  });
  check(
    "csv import confirm",
    importConfirm.status === 201 && importConfirm.body.created_bottles === 1,
    importConfirm,
    failures,
  );

  const labelUpload = await uploadFile(
    "/api/intake/label-images",
    "QA_Label_Estate_Grand_Vin_2019_750ml.jpg",
    "image/jpeg",
    new Uint8Array([255, 216, 255, 224, 0, 16]),
  );
  check(
    "label image upload",
    labelUpload.status === 201 && labelUpload.body.sha256?.length === 64 && labelUpload.body.file_path?.startsWith("uploads/labels/"),
    labelUpload,
    failures,
  );

  const labelDraft = await req("POST", "/api/intake/label-drafts", {
    upload_id: labelUpload.body.id,
  });
  check(
    "label draft",
    labelDraft.status === 200 &&
      labelDraft.body.confidence === "low" &&
      labelDraft.body.candidate_fields.producer_name === "QA Label",
    labelDraft,
    failures,
  );

  const labelConfirm = await req("POST", "/api/intake/label-drafts/confirm", {
    upload_id: labelUpload.body.id,
    producer_name: "QA Label Estate",
    wine_name: "Grand Vin",
    vintage_year: 2019,
    bottle_size_ml: 750,
    location_id: locations[7].id,
    country: "France",
    region: "Bordeaux",
    type: "red",
    notes: "qa label intake",
  });
  check("label confirm via ledger", labelConfirm.status === 201 && labelConfirm.body.transaction_type === "IN", labelConfirm, failures);

  const labelTimeline = await req("GET", `/api/bottles/${labelConfirm.body.bottle_id}/transactions`);
  check(
    "label timeline",
    labelTimeline.status === 200 &&
      labelTimeline.body.map((item) => item.transaction_type).join(",") === "IN" &&
      labelTimeline.body[0].actor === "label_intake",
    labelTimeline,
    failures,
  );

  const occupiedAdd = await req("POST", "/api/bottles", {
    vintage_id: vintage.body.id,
    current_location_id: locations[2].id,
  });
  check("occupied target rejected", occupiedAdd.status === 409, occupiedAdd, failures);

  const move = await req("POST", "/api/inventory-transactions", {
    bottle_id: bConsume.id,
    transaction_type: "MOVE",
    from_location_id: locations[0].id,
    to_location_id: locations[1].id,
    note: "QA移动",
  });
  check(
    "move bottle",
    move.status === 201 && move.body.from_location_code === "Q-01-01" && move.body.to_location_code === "Q-01-02",
    move,
    failures,
  );

  const staleMove = await req("POST", "/api/inventory-transactions", {
    bottle_id: bConsume.id,
    transaction_type: "MOVE",
    from_location_id: locations[0].id,
    to_location_id: locations[5].id,
    note: "stale",
  });
  check("invalid MOVE rejected", staleMove.status === 409, staleMove, failures);

  const consume = await req("POST", "/api/inventory-transactions", {
    bottle_id: bConsume.id,
    transaction_type: "CONSUME",
    note: "QA饮用",
  });
  check("consume bottle", consume.status === 201, consume, failures);

  const gift = await req("POST", "/api/inventory-transactions", {
    bottle_id: bGift.id,
    transaction_type: "GIFT",
    note: "QA送礼",
  });
  check("gift bottle", gift.status === 201, gift, failures);

  const damage = await req("POST", "/api/inventory-transactions", {
    bottle_id: bDamage.id,
    transaction_type: "DAMAGE",
    note: "QA损耗",
  });
  check("damage bottle", damage.status === 201, damage, failures);

  const adjust = await req("POST", "/api/inventory-transactions", {
    bottle_id: bAdjust.id,
    transaction_type: "ADJUST",
    from_location_id: locations[4].id,
    note: "QA盘亏",
  });
  check("adjust bottle", adjust.status === 201, adjust, failures);

  for (const [bottle, label] of [
    [bConsume, "consumed"],
    [bGift, "gifted"],
    [bDamage, "damaged"],
  ]) {
    const retry = await req("POST", "/api/inventory-transactions", {
      bottle_id: bottle.id,
      transaction_type: "MOVE",
      to_location_id: locations[6].id,
      note: "should reject",
    });
    check(`${label} bottle cannot move again`, retry.status === 409, retry, failures);
  }

  const states = await Promise.all([bConsume, bGift, bDamage, bAdjust].map((bottle) => req("GET", `/api/bottles/${bottle.id}`)));
  check("statuses updated", states.map((item) => item.body.current_status).join(",") === "drunk,gifted,damaged,lost", states.map((item) => item.body), failures);
  check("locations cleared", states.every((item) => item.body.current_location_id === null), states.map((item) => item.body), failures);

  const timeline = await req("GET", `/api/bottles/${bConsume.id}/transactions`);
  check("transaction history complete", timeline.status === 200 && timeline.body.map((item) => item.transaction_type).join(",") === "IN,MOVE,CONSUME", timeline, failures);

  const dashboard = await req("GET", "/api/dashboard/summary");
  check(
    "dashboard state is consistent",
    dashboard.status === 200 &&
      dashboard.body.total_bottles === 6 &&
      dashboard.body.in_stock_bottles === 2 &&
      dashboard.body.cellar_occupancy[0].occupied === 2,
    dashboard,
    failures,
  );

  const csv = await fetch(`${base}/api/export/bottles.csv`);
  const csvText = await csv.text();
  check(
    "export CSV",
      csv.status === 200 &&
      csvText.includes("QA Estate") &&
      csvText.includes("QA Import Estate") &&
      csvText.includes("QA Label Estate") &&
      csvText.includes("gifted") &&
      csvText.includes("damaged") &&
      csvText.includes("lost"),
    { status: csv.status, head: csvText.split("\n").slice(0, 3) },
    failures,
  );

  const result = {
    failures,
    summary: {
      locationCount: locations.length,
      statuses: states.map((item) => item.body.current_status),
      timeline: timeline.body.map((item) => item.transaction_type),
      dashboard: {
        total_bottles: dashboard.body.total_bottles,
        in_stock_bottles: dashboard.body.in_stock_bottles,
        cellar_occupied: dashboard.body.cellar_occupancy[0].occupied,
      },
      labelBottle: labelConfirm.body.bottle_id,
      importedBottles: importConfirm.body.created_bottles,
      csvLines: csvText.split("\n").length,
    },
  };
  console.log(JSON.stringify(result, null, 2));
  if (failures.length) process.exitCode = 1;
}

removeGeneratedPath(dbFile);
removeGeneratedPath(dataDir, { recursive: true });

const api = spawn(python, ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(port)], {
  cwd: apiDir,
  env: {
    ...process.env,
    WINE_CELLAR_DATABASE_URL: "sqlite:///./.alpha-qa-smoke.db",
    WINE_CELLAR_DATA_DIR: dataDir,
    WINE_CELLAR_LABEL_UPLOAD_DIR: path.join(dataDir, "uploads", "labels"),
  },
  stdio: ["ignore", "pipe", "pipe"],
});

let stderr = "";
api.stderr.on("data", (chunk) => {
  stderr += chunk.toString();
});

try {
  await waitForApi(api);
  await runSmoke();
} catch (error) {
  console.error(error);
  if (stderr) console.error(stderr);
  process.exitCode = 1;
} finally {
  api.kill();
  await sleep(250);
  removeGeneratedPath(dbFile);
  removeGeneratedPath(dataDir, { recursive: true });
}
