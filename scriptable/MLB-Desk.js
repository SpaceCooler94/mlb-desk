// Variables used by Scriptable.
// These must be at the very top of the file. Do not edit.
// icon-color: red; icon-glyph: baseball;
// MLB Desk — opens the game-sheet layout from the reference card.
// Private repo: Keychain.set("mlbDeskGithubToken", "ghp_...")

const OWNER = "SpaceCooler94";
const REPO = "mlb-desk";
const BRANCH = "main";
const FEED_PATH = "feed/current.json";
const SPORT = "mlb";
const TOKEN_KEY = "mlbDeskGithubToken";
const UA = "mlb-desk-scriptable";

const NAMES = {
  NYY:"YANKEES",LAD:"DODGERS",SF:"GIANTS",SD:"PADRES",COL:"ROCKIES",TEX:"RANGERS",
  TOR:"BLUE JAYS",BOS:"RED SOX",TB:"RAYS",CWS:"WHITE SOX",DET:"TIGERS",MIL:"BREWERS",
  BAL:"ORIOLES",CHC:"CUBS",CIN:"REDS",ATL:"BRAVES",HOU:"ASTROS",WSH:"NATIONALS",
  STL:"CARDINALS",MIN:"TWINS",LAA:"ANGELS",MIA:"MARLINS",ARI:"D-BACKS",PHI:"PHILLIES",
  NYM:"METS",CLE:"GUARDIANS",KC:"ROYALS",PIT:"PIRATES",SEA:"MARINERS",ATH:"ATHLETICS"
};

function feedUrl() {
  return "https://raw.githubusercontent.com/" + OWNER + "/" + REPO + "/" + BRANCH + "/" + FEED_PATH + "?t=" + Date.now();
}
function apiUrl() {
  return "https://api.github.com/repos/" + OWNER + "/" + REPO + "/contents/" + FEED_PATH + "?ref=" + BRANCH;
}
function token() {
  try { if (Keychain.contains(TOKEN_KEY)) return Keychain.get(TOKEN_KEY); } catch (e) {}
  return null;
}
async function loadCard() {
  const hdrs = { "User-Agent": UA };
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
  if (n === null || n === undefined || isNaN(Number(n))) return "—";
  const v = Number(n);
  return (v > 0 ? "+" : "") + v.toFixed(1);
}
function grade(p) {
  const z = p.sigma ? Math.abs(Number(p.edge) || 0) / Number(p.sigma) : Math.abs(Number(p.edge) || 0);
  if (p.play === "OVER" || p.play === "UNDER") return "A";
  if (Math.abs(Number(p.edge) || 0) >= 0.8) return "A";
  if (p.play === "WATCH") return "A-";
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
function esc(s) {
  return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
}
function badgeClass(score) {
  const n = Number(score);
  if (n >= 70) return "g";
  if (n <= 20) return "r";
  return "y";
}
function looksFor(g, rows) {
  if (g.looks && g.looks.length) return g.looks;
  return rows.slice(0, 8).map((p) => ({
    side: p.team === g.home ? "home" : "away",
    player: p.player,
    pos: p.pos || "",
    note: (p.market_label || p.market || "") + " · " + (p.play || ""),
    score: p.p_over != null ? Math.round(Number(p.p_over) * 100) : 50
  }));
}
function sheetCSS() {
  return ":root{--bg:#0a0c10;--ink:#f3f5f8;--mute:#8b93a2;--pink:#ff2d7b;--good:#3DDC97;--bad:#e35d6a}*{box-sizing:border-box}html,body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.35 -apple-system}.wrap{max-width:920px;margin:0 auto;padding:16px 14px 48px}.kicker{display:flex;justify-content:space-between;align-items:center}.kicker-l{font-size:11px;letter-spacing:.14em;color:var(--mute);font-weight:700}.kicker-l b{display:inline-block;background:#1c212b;color:#fff;padding:3px 8px;border-radius:4px;margin-right:8px}.logo{font-weight:900;font-size:26px}.logo span{color:var(--pink)}h1{font-size:30px;margin:8px 0 6px;font-weight:800}.meta{color:var(--mute);font-size:11px;letter-spacing:.08em;text-transform:uppercase;margin-bottom:12px}.teams{display:grid;grid-template-columns:1fr 42px 1fr;border-radius:12px;overflow:hidden;margin-bottom:10px}.away{background:linear-gradient(90deg,#0a3d44,#0e5560);padding:16px 14px}.home{background:linear-gradient(90deg,#9a3a12,#d2551a);padding:16px 14px;text-align:right}.lab{font-size:10px;opacity:.75}.nm{font-size:20px;font-weight:800}.imp{font-size:11px;opacity:.88}.at{display:grid;place-items:center;font-weight:800}.pills{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:0 0 12px}.pill{background:#12151c;border:1px solid #232833;border-radius:10px;padding:11px 6px;text-align:center}.pill .k{font-size:9px;color:var(--mute);letter-spacing:.14em;font-weight:700}.pill .v{font-size:14px;font-weight:800;margin-top:4px}.panel{background:#12151c;border:1px solid #232833;border-radius:12px;padding:12px;margin-bottom:10px}.ph{display:flex;justify-content:space-between;margin:2px 0 8px}.ph b{font-size:12px;letter-spacing:.1em;border-left:3px solid var(--pink);padding-left:8px}.ph span{font-size:10px;color:var(--mute)}table{width:100%;border-collapse:collapse}th{text-align:left;font-size:10px;color:var(--mute);padding:6px 4px}th.r,td.r{text-align:right}td{padding:11px 4px;border-top:1px solid #232833}.who{display:flex;gap:10px;align-items:center}.dot{width:22px;height:22px;border-radius:50%;background:#1d232d;display:grid;place-items:center;font-size:8px;font-weight:800}.pn{font-weight:700}.ps{font-size:11px;color:var(--mute)}.pos{color:var(--good);font-weight:700}.neg{color:var(--bad);font-weight:700}.grade{font-weight:800;color:var(--pink);font-size:16px}.cols{display:grid;grid-template-columns:1fr 1fr;gap:8px}.col h3{font-size:11px;color:var(--mute);margin:0 0 6px}.mrow{display:flex;justify-content:space-between;align-items:center;padding:9px 2px;border-top:1px solid #232833}.badge{min-width:34px;text-align:center;font-weight:800;padding:4px 6px;border-radius:6px}.g{background:#16361f;color:#3DDC97}.y{background:#3a3210;color:#e8c547}.r{background:#3a1518;color:#ff6b6b}.foot{display:flex;justify-content:space-between;color:var(--mute);font-size:11px}.foot b{color:var(--pink)}";
}
function lookCol(title, items) {
  const body = items.map((x) => "<div class=\"mrow\"><div><div class=\"pn\">" + esc(x.player) + "</div><div class=\"ps\">" + esc([x.pos, x.note].filter(Boolean).join(" · ")) + "</div></div><div class=\"badge " + badgeClass(x.score) + "\">" + esc(x.score) + "</div></div>").join("") || "<div class=\"ps\">No tagged looks</div>";
  return "<div class=\"col\"><h3>" + esc(title) + "</h3>" + body + "</div>";
}
function sheetHTML(card, g) {
  const rows = propsFor(card, g.id);
  const week = String(card.date || "").slice(5);
  const ai = g.away_sp || "";
  const hi = g.home_sp || "";
  const pills = [["AWAY SP", g.away_sp || "—"],["HOME SP", g.home_sp || "—"],["PARK", g.park || "—"],["FIRST PITCH", g.when || "—"]];
  const pillHTML = pills.map((x) => "<div class=\"pill\"><div class=\"k\">" + esc(x[0]) + "</div><div class=\"v\">" + esc(x[1]) + "</div></div>").join("");
  const body = rows.map((p) => {
    const gapCls = Number(p.edge) >= 0 ? "pos" : "neg";
    return "<tr><td><div class=\"who\"><div class=\"dot\">" + esc(p.team || "") + "</div><div><div class=\"pn\">" + esc(p.player) + "</div><div class=\"ps\">" + esc([p.pos, p.market_label || p.market].filter(Boolean).join(" · ")) + "</div></div></div></td><td class=\"r\">" + (p.proj != null ? p.proj : "—") + "</td><td class=\"r\">" + (p.line != null ? p.line : "—") + "</td><td class=\"r " + gapCls + "\">" + fmt(p.edge) + "</td><td class=\"r grade\">" + grade(p) + "</td></tr>";
  }).join("") || "<tr><td colspan=\"5\">No props</td></tr>";
  const looks = looksFor(g, rows);
  const whenLine = [g.when, g.venue || g.park].filter(Boolean).join(" · ");
  return "<!DOCTYPE html><html><head><meta charset=\"utf-8\"/><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"/><style>" + sheetCSS() + "</style></head><body><div class=\"wrap\"><div class=\"kicker\"><div class=\"kicker-l\"><b>" + esc(week) + "</b> MLB · GAME SHEET</div><div class=\"logo\"><span>x</span>DESK</div></div><h1>" + esc(nameOf(g.away)) + " AT " + esc(nameOf(g.home)) + "</h1><div class=\"meta\">" + esc(whenLine) + "</div><div class=\"teams\"><div class=\"away\"><div class=\"lab\">AWAY</div><div class=\"nm\">" + esc(nameOf(g.away)) + "</div><div class=\"imp\">" + esc(ai) + "</div></div><div class=\"at\">AT</div><div class=\"home\"><div class=\"lab\">HOME</div><div class=\"nm\">" + esc(nameOf(g.home)) + "</div><div class=\"imp\">" + esc(hi) + "</div></div></div><div class=\"pills\">" + pillHTML + "</div><div class=\"panel\"><div class=\"ph\"><b>PROPS AT A GLANCE</b></div><table><thead><tr><th>PLAYER</th><th class=\"r\">PROJ</th><th class=\"r\">LINE</th><th class=\"r\">GAP</th><th class=\"r\">GRADE</th></tr></thead><tbody>" + body + "</tbody></table></div><div class=\"panel\"><div class=\"ph\"><b>KEY MATCHUPS</b></div><div class=\"cols\">" + lookCol((g.home || "") + " LOOKS", looks.filter((x) => x.side === "home")) + lookCol((g.away || "") + " LOOKS", looks.filter((x) => x.side === "away")) + "</div></div><div class=\"foot\"><div><b>desk</b> · research</div><div>" + esc(card.status || "") + "</div></div></div></body></html>";
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
    row.height = 54;
    row.dismissOnSelect = true;
    row.onSelect = async () => { await presentSheet(card, g); };
    const t = row.addText(nameOf(g.away) + " AT " + nameOf(g.home) + "\n" + (g.when || "") + " · " + n + " props");
    t.titleFont = Font.boldSystemFont(16);
    table.addRow(row);
  }
  await table.present();
}
function buildWidget(card) {
  const w = new ListWidget();
  w.backgroundColor = new Color("#0a0c10");
  w.setPadding(12, 14, 12, 14);
  const g = gamesFrom(card)[0] || {};
  const p = propsFor(card, g.id)[0];
  const k = w.addText((card.date || "") + "  ·  GAME SHEET");
  k.font = Font.boldSystemFont(10);
  k.textColor = new Color("#8b93a2");
  const title = w.addText(nameOf(g.away) + " AT " + nameOf(g.home));
  title.font = Font.boldSystemFont(16);
  title.textColor = Color.white();
  w.addSpacer(8);
  if (p) {
    const nm = w.addText(p.player);
    nm.font = Font.boldSystemFont(15);
    nm.textColor = Color.white();
    const gap = w.addText((p.proj != null ? p.proj : "—") + " vs " + (p.line != null ? p.line : "—") + "   " + fmt(p.edge));
    gap.font = Font.mediumSystemFont(12);
    gap.textColor = Number(p.edge) >= 0 ? new Color("#3DDC97") : new Color("#e35d6a");
  }
  w.addSpacer();
  const f = w.addText("xDESK");
  f.font = Font.boldSystemFont(12);
  f.textColor = new Color("#ff2d7b");
  return w;
}
async function run() {
  let card;
  try { card = await loadCard(); }
  catch (e) {
    if (config.runsInWidget) { const w = new ListWidget(); w.addText("Feed failed"); Script.setWidget(w); Script.complete(); return; }
    const a = new Alert(); a.title = "Desk feed failed"; a.message = String(e); a.addAction("OK"); await a.present(); Script.complete(); return;
  }
  if (config.runsInWidget) { Script.setWidget(buildWidget(card)); Script.complete(); return; }
  await pickGame(card);
  Script.complete();
}
await run();
