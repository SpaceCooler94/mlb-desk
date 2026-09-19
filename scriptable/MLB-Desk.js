// MLB Desk — Scriptable (player props)
// Fetches feed/current.json. Same pattern as NFL Desk.
//
// Setup: paste into Scriptable as "MLB Desk"
// Private repo: Keychain.set("mlbDeskGithubToken", "ghp_...")

const OWNER = "SpaceCooler94";
const REPO = "mlb-desk";
const BRANCH = "main";
const FEED_PATH = "feed/current.json";
const EDGE_FLAG = 0.8;

function feedUrl() {
  return (
    "https://raw.githubusercontent.com/" +
    OWNER + "/" + REPO + "/" + BRANCH + "/" + FEED_PATH +
    "?t=" + Date.now()
  );
}

function apiUrl() {
  return (
    "https://api.github.com/repos/" +
    OWNER + "/" + REPO + "/contents/" + FEED_PATH + "?ref=" + BRANCH
  );
}

function token() {
  try {
    if (Keychain.contains("mlbDeskGithubToken")) {
      return Keychain.get("mlbDeskGithubToken");
    }
  } catch (e) {}
  return null;
}

async function loadCard() {
  const hdrs = { "User-Agent": "mlb-desk-scriptable" };
  const tok = token();
  if (tok) hdrs.Authorization = "Bearer " + tok;
  try {
    const raw = new Request(feedUrl());
    raw.headers = hdrs;
    raw.timeoutInterval = 20;
    return await raw.loadJSON();
  } catch (err) {
    const req = new Request(apiUrl());
    req.headers = Object.assign({}, hdrs, { Accept: "application/vnd.github.raw+json" });
    req.timeoutInterval = 20;
    return await req.loadJSON();
  }
}

function fmt(n, d) {
  if (n === null || n === undefined || isNaN(n)) return "—";
  const v = Number(n);
  const s = v.toFixed(d === undefined ? 1 : d);
  return (v > 0 ? "+" : "") + s;
}

function american(n) {
  if (n === null || n === undefined) return "";
  const v = Number(n);
  return (v > 0 ? "+" : "") + String(v);
}

function playColor(play) {
  if (play === "OVER" || play === "UNDER") return new Color("#3DDC97");
  if (play === "WATCH") return new Color("#FF9F0A");
  return new Color("#8E8E93");
}

function impliedOver(americanPrice) {
  if (americanPrice === null || americanPrice === undefined) return null;
  const o = Number(americanPrice);
  if (o < 0) return (-o) / ((-o) + 100);
  return 100 / (o + 100);
}

function propLine(p) {
  const side = p.edge != null && Number(p.edge) < 0 ? "U" : "O";
  return side + " " + (p.line != null ? p.line : "—") + "   proj " + (p.proj != null ? p.proj : "—");
}

function sortedProps(card) {
  const rows = (card.props || []).slice();
  rows.sort((a, b) => {
    const rank = { OVER: 0, UNDER: 0, WATCH: 1, PASS: 2 };
    const ra = rank[a.play] != null ? rank[a.play] : 3;
    const rb = rank[b.play] != null ? rank[b.play] : 3;
    if (ra !== rb) return ra - rb;
    return Math.abs(b.edge || 0) - Math.abs(a.edge || 0);
  });
  return rows;
}

async function presentTable(card) {
  const table = new UITable();
  table.showSeparators = true;

  const head = new UITableRow();
  head.isHeader = true;
  head.height = 44;
  const tag = card.status === "SEED_PRIOR" ? "SEED — do not bet" : "LIVE props";
  head.addText("MLB  " + (card.date || "") + "  PROPS   " + tag);
  table.addRow(head);

  const sub = new UITableRow();
  sub.height = 36;
  sub.addText(card.disclaimer || "");
  table.addRow(sub);

  for (const p of sortedProps(card)) {
    const row = new UITableRow();
    row.height = 58;
    row.cellSpacing = 6;
    row.onSelect = () => showProp(card, p);

    const left = row.addText(p.when + "\n" + p.team + " vs " + p.opp);
    left.widthWeight = 22;
    left.titleFont = Font.systemFont(11);
    left.subtitleFont = Font.systemFont(11);

    const mid = row.addText(p.player + "\n" + (p.market_label || p.market));
    mid.widthWeight = 36;
    mid.titleFont = Font.mediumSystemFont(14);
    mid.subtitleFont = Font.systemFont(11);

    const right = row.addText(propLine(p) + "\nΔ " + fmt(p.edge));
    right.widthWeight = 26;
    right.titleFont = Font.systemFont(12);
    right.titleColor =
      Math.abs(p.edge || 0) >= EDGE_FLAG ? new Color("#FF9F0A") : new Color("#EBEBF5");

    const badge = row.addText(p.play || "PASS");
    badge.widthWeight = 16;
    badge.titleColor = playColor(p.play);
    badge.titleFont = Font.boldSystemFont(12);

    table.addRow(row);
  }

  await table.present();
}

async function showProp(card, p) {
  const imp = impliedOver(p.price);
  const a = new Alert();
  a.title = p.player;
  a.message = [
    p.team + " vs " + p.opp + "   " + p.when,
    (p.market_label || p.market) + "  " + (p.line != null ? p.line : "—"),
    "Book: " + (p.book || "—") + "  " + american(p.price),
    "Proj: " + (p.proj != null ? p.proj : "—") + "   σ " + (p.sigma != null ? p.sigma : "—"),
    "P(over): " + (p.p_over != null ? (100 * p.p_over).toFixed(0) + "%" : "—") +
      (imp != null ? "   mkt " + (100 * imp).toFixed(0) + "%" : ""),
    "Edge (proj-line): " + fmt(p.edge),
    "Play: " + p.play + "   Units: " + (p.units ?? 0),
    "",
    p.note || "No note",
    "",
    "Card: " + card.status
  ].join("\n");
  a.addAction("OK");
  await a.present();
}

function topWatch(card) {
  const rows = sortedProps(card);
  return rows.find((p) => p.play === "WATCH" || p.play === "OVER" || p.play === "UNDER") || rows[0];
}

function buildWidget(card) {
  const w = new ListWidget();
  w.backgroundColor = new Color("#0B0F14");
  w.setPadding(12, 14, 12, 14);

  const kicker = w.addText("MLB DESK PROPS  ·  " + (card.date || ""));
  kicker.font = Font.boldSystemFont(10);
  kicker.textColor = new Color("#8E8E93");

  const banner = w.addText(card.status === "SEED_PRIOR" ? "SEED CARD" : "LIVE");
  banner.font = Font.boldSystemFont(16);
  banner.textColor =
    card.status === "SEED_PRIOR" ? new Color("#FF9F0A") : new Color("#3DDC97");

  w.addSpacer(6);
  const p = topWatch(card);
  if (!p) {
    w.addText("No props in feed");
    return w;
  }

  const name = w.addText(p.player);
  name.font = Font.boldSystemFont(18);
  name.textColor = Color.white();

  const mkt = w.addText((p.market_label || p.market) + "  " + (p.line != null ? p.line : ""));
  mkt.font = Font.systemFont(12);
  mkt.textColor = new Color("#EBEBF5");

  const edge = w.addText(
    "Proj " + (p.proj != null ? p.proj : "—") +
      "   Δ " + fmt(p.edge) +
      "   " + p.play
  );
  edge.font = Font.mediumSystemFont(12);
  edge.textColor = playColor(p.play);

  w.addSpacer();
  const foot = w.addText(p.team + " vs " + p.opp + "  " + (p.when || ""));
  foot.font = Font.systemFont(9);
  foot.textColor = new Color("#636366");
  return w;
}

async function run() {
  let card;
  try {
    card = await loadCard();
  } catch (e) {
    if (config.runsInWidget) {
      const w = new ListWidget();
      w.addText("Feed failed");
      w.addText(String(e));
      Script.setWidget(w);
      Script.complete();
      return;
    }
    const a = new Alert();
    a.title = "MLB Desk feed failed";
    a.message = String(e);
    a.addAction("OK");
    await a.present();
    Script.complete();
    return;
  }

  if (config.runsInWidget) {
    Script.setWidget(buildWidget(card));
    Script.complete();
    return;
  }

  await presentTable(card);
  Script.complete();
}

await run();
