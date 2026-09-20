# MLB Desk

Same machine as [nfl-desk](https://github.com/SpaceCooler94/nfl-desk): a daily **player-prop** card on GitHub that Scriptable reads on iPhone.

The repo **always** ships the xDESK game-sheet layout. That is the product. Same card as NFL Desk:

```
DATE            MLB · GAME SHEET                              xDESK
AWAY AT HOME
[teal AWAY | AT | orange HOME]
AWAY SP · HOME SP · PARK · FIRST PITCH
PROPS AT A GLANCE     PLAYER · PROJ · LINE · GAP · GRADE
KEY MATCHUPS          0–100 badges
```

Do not replace this with a native UITable or a list-only view. If the sheet and the feed disagree, fix the feed.

Sister research board: [moonshot-hr](https://github.com/SpaceCooler94/moonshot-hr) (Statcast HR). This repo is the betting-desk feed.

## Phone

1. Copy [scriptable/MLB-Desk.js](https://raw.githubusercontent.com/SpaceCooler94/mlb-desk/main/scriptable/MLB-Desk.js)
2. Scriptable → New Script → paste → name `MLB Desk`
3. Run. Pick a game. You get the game sheet. Widget works on the same script.

Feed URL (already baked into the JS):

https://raw.githubusercontent.com/SpaceCooler94/mlb-desk/main/feed/current.json

Sheet preview:

https://htmlpreview.github.io/?https://raw.githubusercontent.com/SpaceCooler94/mlb-desk/main/web/index.html?sport=mlb

## Layout contract (do not drift)

| Surface | Must render |
|---|---|
| `scriptable/MLB-Desk.js` | WebView game sheet (banner, 4 pills, props table, key matchups) |
| `web/index.html` | Same sheet, fed by `feed/current.json` |
| `feed/current.json` | `games[]` + `props[]`. Optional `looks[]` on a game. |

Pills are always **AWAY SP / HOME SP / PARK / FIRST PITCH**.
Table columns are always **PLAYER / PROJ / LINE / GAP / GRADE**.

## What we price

| Market | Typical line | σ (seed) |
|---|---|---|
| Pitcher strikeouts | 4.5–7.5 | 1.8 |
| Pitcher outs | 15.5–18.5 | 3.5 |
| Hits | 0.5 / 1.5 | 0.7 |
| Total bases | 1.5 / 2.5 | 1.1 |
| HR (yes) | +300 to +600 | binary |
| Hits+runs+RBI | 1.5 / 2.5 | 1.2 |
| Stolen bases | 0.5 | binary-ish |

## Daily loop

Morning: lineups + starter pitch counts
Noon: push `feed/current.json` (sheet files stay put)
First pitch: lock
Night: grade Ks / TB / HR vs close

`SEED_PRIOR` until we grade 2–3 weeks of this feed. Units stay 0 unless you size a ticket.
