// Variables used by Scriptable.
// These must be at the very top of the file. Do not edit.
// icon-color: red; icon-glyph: baseball;
// MLB Desk — game sheet. Fetches feed/current.json.
// Private repo: Keychain.set("mlbDeskGithubToken", "ghp_...")

const OWNER = "SpaceCooler94";
const REPO = "mlb-desk";
const BRANCH = "main";
const FEED_PATH = "feed/current.json";
const NAMES = {NYY:"YANKEES",LAD:"DODGERS",SF:"GIANTS",SD:"PADRES",COL:"ROCKIES",TEX:"RANGERS",TOR:"BLUE JAYS",BOS:"RED SOX",TB:"RAYS",CWS:"WHITE SOX",DET:"TIGERS",MIL:"BREWERS",BAL:"ORIOLES",CHC:"CUBS",CIN:"REDS",ATL:"BRAVES",HOU:"ASTROS",WSH:"NATIONALS",STL:"CARDINALS",MIN:"TWINS",LAA:"ANGELS",MIA:"MARLINS",ARI:"D-BACKS",PHI:"PHILLIES",NYM:"METS",CLE:"GUARDIANS",KC:"ROYALS",PIT:"PIRATES",SEA:"MARINERS",ATH:"ATHLETICS"};

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
function grade(p) {
  const z = p.sigma ? Math.abs(Number(p.edge) || 0) / Number(p.sigma) : Math.abs(Number(p.edge) || 0);
  if (p.play === "OVER" || p.play === "UNDER") return "A";
  if (p.play === "WATCH" && z >= 0.45) return "A-";
  if (p.play === "WATCH") return "B+";
  return "C";
}
function fmt(n) {
  if (n == null || isNaN(Number(n))) return "—";
  const v = Number(n);
  return (v > 0 ? "+" : "") + v.toFixed(1);
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
function esc(s) {
  return String(s == null ? "" : s).replace(/&/g, "&").replace(/</g, "<").replace(/"/g, """);
}
function pill(k, v) {
  return "<div class=\"pill\"><div class=\"k\">" + esc(k) + "</div><div class=\"v\">" + esc(String(v)) + "</div></div>";
}
function lookCol(team, rows) {
  const body = rows.slice(0, 4).map((p) => {
    const z = Math.abs(Number(p.edge) || 0);
    const cls = (p.sigma && z / p.sigma >= 0.6) || z >= 1 ? "g" : z >= 0.5 ? "y" : "r";
    const score = p.p_over != null ? Math.round(Number(p.p_over) * 100) : Math.min(99, Math.round(50 + z * 10));
    return "<div class=\"mrow\"><div><div class=\"pn\">" + esc(p.player) + "</div><div class=\"ps\">" + esc(p.market_label || p.market) + " · " + esc(p.play) + "</div></div><div class=\"badge " + cls + "\">" + score + "</div></div>";
  }).join("") || "<div class=\"ps\">No tagged looks</div>";
  return "<div><div class=\"ps\">" + esc(team || "") + " LOOKS</div>" + body + "</div>";
}
function sheetHTML(card, g) {
  const rows = propsFor(card, g.id);
  const week = String(card.date || "").slice(5);
  const ai = g.away_sp || "";
  const hi = g.home_sp || "";
  const pills = pill("AWAY SP", g.away_sp || "—") + pill("HOME SP", g.home_sp || "—") + pill("PARK", g.park || "—") + pill("FIRST PITCH", g.when || "—");
  const body = rows.map((p) => {
    const gapCls = Number(p.edge) >= 0 ? "pos" : "neg";
    return "<tr><td><div class=\"who\"><div class=\"dot\">" + (p.team || "") + "</div><div><div class=\"pn\">" + esc(p.player) + "</div><div class=\"ps\">" + esc(p.pos || "") + " · " + esc(p.market_label || p.market) + "</div></div></div></td><td class=\"num\">" + (p.proj != null ? p.proj : "—") + "</td><td class=\"num\">" + (p.line != null ? p.line : "—") + "</td><td class=\"num " + gapCls + "\">" + fmt(p.edge) + "</td><td class=\"num grade\">" + grade(p) + "</td></tr>";
  }).join("") || "<tr><td colspan=\"5\" class=\"ps\">No props</td></tr>";
  return "<!DOCTYPE html><html><head><meta charset=\"utf-8\"/><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"/><style>body{margin:0;background:#0b0d12;color:#f4f6fb;font:14px/1.4 -apple-system}.wrap{padding:18px 14px 36px}.kicker{display:flex;justify-content:space-between;align-items:center}.kicker b{background:#1b1f28;padding:3px 7px;border-radius:4px;margin-right:8px;font-size:11px}.logo{font-weight:800;font-size:22px}.logo span{color:#ff2d7b}h1{font-size:26px;margin:10px 0 6px}.meta{color:#9aa3b2;font-size:11px;text-transform:uppercase}.teams{display:grid;grid-template-columns:1fr 36px 1fr;margin:14px 0 10px;border-radius:10px;overflow:hidden}.away{background:linear-gradient(90deg,#08363c,#0f4b52);padding:14px}.home{background:linear-gradient(90deg,#8a3414,#c24a18);padding:14px;text-align:right}.lab{font-size:10px;opacity:.8}.nm{font-size:16px;font-weight:800}.imp{font-size:11px;opacity:.85}.at{display:grid;place-items:center;font-weight:800}.pills{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-bottom:12px}.pill{background:#12151c;border:1px solid #232833;border-radius:10px;padding:10px 6px;text-align:center}.pill .k{font-size:9px;color:#9aa3b2}.pill .v{font-size:12px;font-weight:800;margin-top:3px}.panel{background:#12151c;border:1px solid #232833;border-radius:12px;padding:12px;margin-bottom:10px}.ph b{border-left:3px solid #ff2d7b;padding-left:8px;font-size:12px}table{width:100%;border-collapse:collapse}th{text-align:left;font-size:10px;color:#9aa3b2;padding:6px}td{padding:9px 6px;border-top:1px solid #232833}.num{text-align:right}.who{display:flex;gap:8px;align-items:center}.dot{width:20px;height:20px;border-radius:50%;background:#1d222c;display:grid;place-items:center;font-size:8px;font-weight:800}.pn{font-weight:700}.ps{font-size:11px;color:#9aa3b2}.pos{color:#3DDC97;font-weight:700}.neg{color:#ff6b6b;font-weight:700}.grade{font-weight:800;color:#ff2d7b}.cols{display:grid;grid-template-columns:1fr 1fr;gap:8px}.mrow{display:flex;justify-content:space-between;padding:7px 2px;border-top:1px solid #232833}.badge{min-width:32px;text-align:center;font-weight:800;padding:3px 5px;border-radius:6px}.g{background:#14351f;color:#3DDC97}.y{background:#3a3210;color:#e8c547}.r{background:#3a1515;color:#ff6b6b}.foot{display:flex;justify-content:space-between;color:#9aa3b2;font-size:11px}.foot b{color:#ff2d7b}</style></head><body><div class=\"wrap\"><div class=\"kicker\"><div><b>" + esc(week) + "</b> MLB · GAME SHEET</div><div class=\"logo\"><span>x</span>DESK</div></div><h1>" + esc(nameOf(g.away)) + " AT " + esc(nameOf(g.home)) + "</h1><div class=\"meta\">" + esc([g.when || "", g.venue || g.park || ""].filter(Boolean).join(" · ")) + "</div><div class=\"teams\"><div class=\"away\"><div class=\"lab\">AWAY</div><div class=\"nm\">" + esc(nameOf(g.away)) + "</div><div class=\"imp\">" + esc(ai) + "</div></div><div class=\"at\">AT</div><div class=\"home\"><div class=\"lab\">HOME</div><div class=\"nm\">" + esc(nameOf(g.home)) + "</div><div class=\"imp\">" + esc(hi) + "</div></div></div><div class=\"pills\">" + pills + "</div><div class=\"panel\"><div class=\"ph\"><b>PROPS AT A GLANCE</b></div><table><thead><tr><th>PLAYER</th><th class=\"num\">PROJ</th><th class=\"num\">LINE</th><th class=\"num\">GAP</th><th class=\"num\">GRADE</th></tr></thead><tbody>" + body + "</tbody></table></div><div class=\"panel\"><div class=\"ph\"><b>KEY LOOKS</b></div><div class=\"cols\">" + lookCol(g.home, rows.filter((p) => p.team === g.home)) + lookCol(g.away, rows.filter((p) => p.team === g.away)) + "</div></div><div class=\"foot\"><div><b>desk</b> · research</div><div>" + esc(card.status || "") + "</div></div></div></body></html>";
}
async function presentSheet(card, g) {
  const wv = new WebView();
  await wv.loadHTML(sheetHTML(card, g));
  await wv.present(true);
}
async function pickGame(card) {
  const games = gamesFrom(card);
  const table = new UITable();
  table.showSeparators = true;
  const head = new UITableRow();
  head.isHeader = true;
  head.addText("MLB  GAME SHEETS");
  table.addRow(head);
  for (const g of games) {
    const n = propsFor(card, g.id).length;
    const row = new UITableRow();
    row.height = 52;
    row.dismissOnSelect = true;
    row.onSelect = async () => { await presentSheet(card, g); };
    const t = row.addText(nameOf(g.away) + " AT " + nameOf(g.home) + "\n" + (g.when || "") + " · " + n + " props");
    t.titleFont = Font.boldSystemFont(15);
    t.subtitleFont = Font.systemFont(11);
    table.addRow(row);
  }
  await table.present();
}
function buildWidget(card) {
  const w = new ListWidget();
  w.backgroundColor = new Color("#0b0d12");
  w.setPadding(12, 14, 12, 14);
  const g = gamesFrom(card)[0] || {};
  const p = propsFor(card, g.id)[0];
  const k = w.addText((card.date || "") + "  ·  GAME SHEET");
  k.font = Font.boldSystemFont(10);
  k.textColor = new Color("#9aa3b2");
  const title = w.addText(nameOf(g.away) + " AT " + nameOf(g.home));
  title.font = Font.boldSystemFont(16);
  title.textColor = Color.white();
  title.minimumScaleFactor = 0.6;
  const sub = w.addText((g.away_sp || "") + " vs " + (g.home_sp || "") + "  " + (g.park || ""));
  sub.font = Font.systemFont(11);
  sub.textColor = new Color("#9aa3b2");
  w.addSpacer(8);
  if (p) {
    const nm = w.addText(p.player);
    nm.font = Font.boldSystemFont(15);
    nm.textColor = Color.white();
    const gap = w.addText((p.market_label || p.market) + "  " + (p.proj != null ? p.proj : "—") + " vs " + (p.line != null ? p.line : "—") + "  " + fmt(p.edge) + "  " + grade(p));
    gap.font = Font.mediumSystemFont(11);
    gap.textColor = Number(p.edge) >= 0 ? new Color("#3DDC97") : new Color("#ff6b6b");
  }
  w.addSpacer();
  const f = w.addText("xDESK  ·  " + (card.status || ""));
  f.font = Font.boldSystemFont(10);
  f.textColor = new Color("#ff2d7b");
  return w;
}
async function run() {
  let card;
  try { card = await loadCard(); }
  catch (e) {
    if (config.runsInWidget) { const w = new ListWidget(); w.addText("Feed failed"); Script.setWidget(w); Script.complete(); return; }
    const a = new Alert(); a.title = "MLB Desk feed failed"; a.message = String(e); a.addAction("OK"); await a.present(); Script.complete(); return;
  }
  if (config.runsInWidget) { Script.setWidget(buildWidget(card)); Script.complete(); return; }
  await pickGame(card);
  Script.complete();
}
await run();
