# MLB Desk

Same machine as [nfl-desk](https://github.com/SpaceCooler94/nfl-desk): a daily **player-prop** card on GitHub that Scriptable reads on iPhone.

Not sides. Not totals. Props only.

Sister research board: [moonshot-hr](https://github.com/SpaceCooler94/moonshot-hr) (Statcast HR). This repo is the betting-desk feed.

## Phone

1. Copy [scriptable/MLB-Desk.js](https://raw.githubusercontent.com/SpaceCooler94/mlb-desk/main/scriptable/MLB-Desk.js)
2. Scriptable → New Script → paste → name `MLB Desk`
3. Run. Widget works on the same script.

Feed URL (already baked into the JS):

https://raw.githubusercontent.com/SpaceCooler94/mlb-desk/main/feed/current.json

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

## Model, week 1 of this desk

Volume × opponent × park × pitcher/batter quality. September innings caps matter more than April ERA.

`SEED_PRIOR` until we grade 2–3 weeks of this feed. Units stay 0 unless you size a ticket.

## Daily loop

Morning: lineups + starter pitch counts  
Noon: push `feed/current.json`  
First pitch: lock  
Night: grade Ks / TB / HR vs close

Same rules as NFL Desk. No parlays of the WATCH column.
