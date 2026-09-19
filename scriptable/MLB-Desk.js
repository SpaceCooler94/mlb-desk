// Variables used by Scriptable.
// These must be at the very top of the file. Do not edit.
// icon-color: red; icon-glyph: baseball;
// MLB Desk — player props, game-sheet theme
// Private repo: Keychain.set("mlbDeskGithubToken", "ghp_...")

const OWNER = "SpaceCooler94";
const REPO = "mlb-desk";
const BRANCH = "main";
const FEED_PATH = "feed/current.json";

const NAMES = {
  NYY: "YANKEES", LAD: "DODGERS", SF: "GIANTS", SD: "PADRES",
  COL: "ROCKIES", TEX: "RANGERS", TOR: "BLUE JAYS", BOS: "RED SOX",
  TB: "RAYS", CWS: "WHITE SOX", DET: "TIGERS", MIL: "BREWERS",
  BAL: "ORIOLES", CHC: "CUBS", CIN: "REDS", ATL: "BRAVES",
  HOU: "ASTROS", WSH: "NATIONALS", STL: "CARDINALS", MIN: "TWINS",
  LAA: "ANGELS", MIA: "MARLINS", ARI: "D-BACKS", PHI: "PHILLIES",
  NYM: "METS", CLE: "GUARDIANS", KC: "ROYALS", PIT: "PIRATES",
  SEA: "MARINERS", ATH: "ATHLETICS"
};

const C = {
  ink: new Color("#F4F6FB"),
  mute: new Color("#9AA3B2"),
  good: new Color("#3DDC97"),
  bad: new Color("#FF6B6B"),
  pink: new Color("#FF2D7B"),
  bg: new Color("#0B0D12")
};

function feedUrl() {
  return "https://raw.githubusercontent.com/" + OWNER + "/" + REPO + "/" + BRANCH + "/" + FEED_PATH + "?t=" + Date.now();
}
function apiUrl() {
  return "https://api.github.com/repos/" + OWNER + "/" + REPO + "/contents/" + FEED_PATH + "?ref=" + BRANCH;
}
function token() {
  try { if (Keychain.contains("mlbDeskGithubToken")) return Keychain.get("mlbDeskGithubToken"); } catch (e) {}
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
function nameOf(ab) { return NAMES[ab] || ab || ""; }
function fmt(n) {
  if (n === null || n === undefined || isNaN(n)) return "—";
  const v = Number(n);
  return (v > 0 ? "+" : "") + v.toFixed(1);
}
function american(n) {
  if (n === null || n === undefined) return "";
  const v = Number(n);
  return (v > 0 ? "+" : "") + String(v);
}
function impliedOver(o) {
  if (o === null || o === undefined) return null;
  o = Number(o);
  return o < 0 ? (-o) / ((-o) + 100) : 100 / (o + 100);
}
function grade(p) {
  const z = p.sigma ? Math.abs(Number(p.edge) || 0) / Number(p.sigma) : Math.abs(Number(p.edge) || 0);
  if (p.play === "OVER" || p.play === "UNDER") return "A";
  if (p.play === "WATCH" && z >= 0.45) return "A-";
  if (p.play === "WATCH") return "B+";
  return "C";
}
function gamesFrom(card) {
  const m = new Map();
  (card.games || []).forEach((g) => m.set(g.id, g));
  (card.props || []).forEach((p) => {
    if (!m.has(p.game_id)) m.set(p.game_id, { id: p.game_id, away: p.team, home: p.opp, when: p.when });
  });
  return [...m.values()];
}
function propsFor(card, gid) {
  return (card.props || []).filter((p) => p.game_id === gid).sort((a, b) => Math.abs(b.edge || 0) - Math.abs(a.edge || 0));
}

async function presentTable(card) {
  const table = new UITable();
  table.showSeparators = true;
  const head = new UITableRow();
  head.isHeader = true;
  head.height = 40;
  const tag = card.status === "SEED_PRIOR" ? "SEED" : "LIVE";
  const h = head.addText((card.date || "") + "  MLB  ·  GAME SHEET    " + tag);
  h.titleFont = Font.boldSystemFont(13);
  table.addRow(head);
  if (card.disclaimer) {
    const sub = new UITableRow();
    sub.height = 32;
    const s = sub.addText(card.disclaimer);
    s.titleColor = C.mute;
    s.titleFont = Font.systemFont(11);
    table.addRow(sub);
  }
  for (const g of gamesFrom(card)) {
    const rows = propsFor(card, g.id);
    const title = new UITableRow();
    title.height = 44;
    const t = title.addText(nameOf(g.away) + " AT " + nameOf(g.home));
    t.titleFont = Font.boldSystemFont(16);
    t.titleColor = C.ink;
    table.addRow(title);
    const pills = new UITableRow();
    pills.height = 28;
    const bits = [g.away_sp, g.home_sp, g.park, g.when].filter(Boolean);
    const ptxt = pills.addText(bits.join("   ·   "));
    ptxt.titleFont = Font.systemFont(11);
    ptxt.titleColor = C.mute;
    table.addRow(pills);
    const cols = new UITableRow();
    cols.height = 22;
    const labels = ["PLAYER", "PROJ", "LINE", "GAP", "GRD"];
    const weights = [46, 14, 14, 14, 12];
    labels.forEach((lab, i) => {
      const c = cols.addText(lab);
      c.widthWeight = weights[i];
      c.titleFont = Font.boldSystemFont(10);
      c.titleColor = C.mute;
    });
    table.addRow(cols);
    if (!rows.length) {
      const empty = new UITableRow();
      empty.addText("No props tagged");
      table.addRow(empty);
      continue;
    }
    for (const p of rows) {
      const row = new UITableRow();
      row.height = 48;
      row.cellSpacing = 4;
      row.onSelect = () => showProp(card, p);
      const left = row.addText(p.player + "\n" + [p.pos, p.market_label || p.market].filter(Boolean).join(" · "));
      left.widthWeight = 46;
      left.titleFont = Font.mediumSystemFont(14);
      left.subtitleFont = Font.systemFont(11);
      left.titleColor = C.ink;
      left.subtitleColor = C.mute;
      const proj = row.addText(p.proj != null ? String(p.proj) : "—");
      proj.widthWeight = 14;
      proj.titleFont = Font.systemFont(13);
      const line = row.addText(p.line != null ? String(p.line) : "—");
      line.widthWeight = 14;
      line.titleFont = Font.systemFont(13);
      const gap = row.addText(fmt(p.edge));
      gap.widthWeight = 14;
      gap.titleFont = Font.boldSystemFont(13);
      gap.titleColor = Number(p.edge) >= 0 ? C.good : C.bad;
      const grd = row.addText(grade(p));
      grd.widthWeight = 12;
      grd.titleFont = Font.boldSystemFont(14);
      grd.titleColor = C.pink;
      table.addRow(row);
    }
  }
  await table.present();
}

async function showProp(card, p) {
  const imp = impliedOver(p.price);
  const a = new Alert();
  a.title = p.player;
  a.message = [
    nameOf(p.team) + " vs " + nameOf(p.opp) + "   " + p.when,
    (p.market_label || p.market) + "  " + (p.line != null ? p.line : "—"),
    "Book: " + (p.book || "—") + "  " + american(p.price),
    "Proj: " + (p.proj != null ? p.proj : "—") + "   σ " + (p.sigma != null ? p.sigma : "—"),
    "P(over): " + (p.p_over != null ? (100 * p.p_over).toFixed(0) + "%" : "—") +
      (imp != null ? "   mkt " + (100 * imp).toFixed(0) + "%" : ""),
    "Gap: " + fmt(p.edge) + "   Grade: " + grade(p),
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
  const rows = (card.props || []).slice().sort((a, b) => Math.abs(b.edge || 0) - Math.abs(a.edge || 0));
  return rows.find((p) => p.play === "WATCH" || p.play === "OVER" || p.play === "UNDER") || rows[0];
}

function buildWidget(card) {
  const w = new ListWidget();
  w.backgroundColor = C.bg;
  w.setPadding(12, 14, 12, 14);
  const games = gamesFrom(card);
  const g = games.find((x) => String(x.when || "").indexOf("FINAL") === -1) || games[0] || {};
  const p = propsFor(card, g.id)[0] || topWatch(card);
  const kicker = w.addText((card.date || "") + "  ·  GAME SHEET");
  kicker.font = Font.boldSystemFont(10);
  kicker.textColor = C.mute;
  const title = w.addText(nameOf(g.away) + " AT " + nameOf(g.home));
  title.font = Font.boldSystemFont(16);
  title.textColor = C.ink;
  title.minimumScaleFactor = 0.6;
  const pills = w.addText([g.away_sp, g.home_sp, g.park].filter(Boolean).join("   "));
  pills.font = Font.systemFont(11);
  pills.textColor = C.mute;
  w.addSpacer(8);
  if (p) {
    const name = w.addText(p.player);
    name.font = Font.boldSystemFont(16);
    name.textColor = C.ink;
    const gap = w.addText(
      (p.market_label || p.market) + "   " +
      (p.proj != null ? p.proj : "—") + " vs " +
      (p.line != null ? p.line : "—") + "   " +
      fmt(p.edge) + "   " + grade(p)
    );
    gap.font = Font.mediumSystemFont(12);
    gap.textColor = Number(p.edge) >= 0 ? C.good : C.bad;
  }
  w.addSpacer();
  const foot = w.addText("desk  ·  " + (card.status || ""));
  foot.font = Font.boldSystemFont(10);
  foot.textColor = C.pink;
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
