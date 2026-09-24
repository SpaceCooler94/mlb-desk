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

| Market | How it is seeded | σ |
|---|---|---|
| Pitcher strikeouts | season K/9 blended with last 5 GS × expected IP × park K | 1.8 |
| Pitcher outs | expected IP × 3 | 3.5 |
| Hits | slot PA × blended AVG × opponent ERA env × park hit | 0.75 |
| Total bases | slot PA × blended SLG × env × park | 1.15 |
| HR (0.5) | slot PA × HR/PA × env × park HR | 0.35 |

Posted numbers in `feed/lines.json` override the seed x.5. Units stay 0 unless you size a ticket.

`SEED_PRIOR` until a card is locked or graded. Lineup tag on each game is `CONFIRMED` / `PROBABLE` / `UNKNOWN`. Batter props only emit when a lineup card is posted (slots 1–6).

This is a projection desk, not a trained classifier. No fake AUC.

## Daily loop

Morning: lineups + starter pitch counts  
Noon: push `feed/current.json` (sheet files stay put)  
First pitch: lock  
Night: grade K / outs / hits / TB / HR vs box

## Daily run

[`.github/workflows/daily-card.yml`](.github/workflows/daily-card.yml) — 08:30 / 11:30 / 18:30 / 01:30 CT, plus **Run workflow** in Actions.

```bash
python3 python/build_day.py --phase auto
python3 python/export_feed.py
python3 python/test_build_day.py
```

| phase | clock (CT) | `status` |
|---|---|---|
| `morning` | 08:30 | `SEED_PRIOR` |
| `noon` | 11:30 | `LIVE` if ≥75% of SPs are named or a card is posted |
| `lock` | 18:30 | `LOCKED` |
| `grade` | 01:30 next day | `GRADED` when boxes land |

Builder source is MLB Stats API only (Rank 1). Empty slate fails closed and does not commit.

```
feed/current.json              Scriptable + web read this
feed/lines.json                optional posted numbers by player
python/build_day.py            slate → card
python/props.py                σ, PA-by-slot, play rule
python/export_feed.py          sheet contract check
.github/workflows/daily-card.yml
scriptable/MLB-Desk.js         iPhone client
```
