# MLB Desk

Same machine as [nfl-desk](https://github.com/SpaceCooler94/nfl-desk): a daily **player-prop** card on GitHub that Scriptable reads on iPhone.

The repo **always** ships the xDESK game-sheet layout. That is the product. Same card as NFL Desk:

```
DATE            MLB \u00b7 GAME SHEET                              xDESK
AWAY AT HOME
[teal AWAY | AT | orange HOME]
AWAY SP \u00b7 HOME SP \u00b7 PARK \u00b7 FIRST PITCH
PROPS AT A GLANCE     PLAYER \u00b7 PROJ \u00b7 LINE \u00b7 GAP \u00b7 GRADE
KEY MATCHUPS          0\u2013100 badges
```

Do not replace this with a native UITable or a list-only view. If the sheet and the feed disagree, fix the feed.

Sister research board: [moonshot-hr](https://github.com/SpaceCooler94/moonshot-hr) (Statcast HR). This repo is the betting-desk feed.

## Phone

1. Copy [scriptable/MLB-Desk.js](https://raw.githubusercontent.com/SpaceCooler94/mlb-desk/main/scriptable/MLB-Desk.js)
2. Scriptable \u2192 New Script \u2192 paste \u2192 name `MLB Desk`
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

| Market | Typical line | \u03c3 (seed) |
|---|---|---|
| Pitcher strikeouts | 4.5\u20137.5 | 1.8 |
| Pitcher outs | 15.5\u201318.5 | 3.5 |
| Hits | 0.5 / 1.5 | 0.7 |
| Total bases | 1.5 / 2.5 | 1.1 |
| HR (yes) | +300 to +600 | binary |
| Hits+runs+RBI | 1.5 / 2.5 | 1.2 |
| Stolen bases | 0.5 | binary-ish |

Auto card seeds **K** and **outs** only. Hits / TB / HR / SB stay manual or come from `feed/lines.json`.

## Daily loop

Morning: lineups + starter pitch counts
Noon: push `feed/current.json` (sheet files stay put)
First pitch: lock
Night: grade Ks / outs vs close

`SEED_PRIOR` until we grade 2\u20133 weeks of this feed. Units stay 0 unless you size a ticket.

## Daily run

[`.github/workflows/daily-card.yml`](.github/workflows/daily-card.yml) \u2014 08:30 / 11:30 / 18:30 / 01:30 CT, plus **Run workflow** in Actions.

```bash
python3 python/build_day.py --phase auto
python3 python/export_feed.py
python3 python/test_build_day.py
```

| phase | clock (CT) | `status` |
|---|---|---|
| `morning` | 08:30 | `SEED_PRIOR` |
| `noon` | 11:30 | `LIVE` if \u226575% of SPs are named |
| `lock` | 18:30 | `LOCKED` |
| `grade` | 01:30 next day | `GRADED` when boxes land |

Builder source is MLB Stats API schedule + probable pitchers + season K/9 \u00d7 expected IP \u00d7 park. Posted numbers override the seed when they exist in `feed/lines.json`. Empty slate fails closed and does not commit.

```
feed/current.json              Scriptable + web read this
feed/lines.json                optional posted K / outs by pitcher
python/build_day.py            slate \u2192 card
python/export_feed.py          sheet contract check
.github/workflows/daily-card.yml
```
