# MLB Desk

Same machine as [nfl-desk](https://github.com/SpaceCooler94/nfl-desk): a daily **player-prop** card on GitHub that Scriptable reads on iPhone.

The repo **always** ships the xDESK game-sheet layout. That is the product.

Sister research board: [moonshot-hr](https://github.com/SpaceCooler94/moonshot-hr) (Statcast HR). This repo is the betting-desk feed.

## Phone

1. Copy [scriptable/MLB-Desk.js](https://raw.githubusercontent.com/SpaceCooler94/mlb-desk/main/scriptable/MLB-Desk.js)
2. Scriptable \u2192 New Script \u2192 paste \u2192 name `MLB Desk`
3. Run. Pick a game. You get the game sheet. Widget works on the same script.

Feed: https://raw.githubusercontent.com/SpaceCooler94/mlb-desk/main/feed/current.json

## Research stack (wired for the job, not the label)

| Library | Job in this repo |
|---|---|
| `pandas` / `numpy` | Season boards and history as frames; feature vectors |
| `pybaseball` | FanGraphs season Barrel%, EV, HardHit%, K%, CSW%. Cached in `data/` |
| `xgboost` | Residual model (`actual - rate proj`) once `feed/history.jsonl` has >=40 graded rows per market |
| `scikit-learn` | Isotonic calibration of `p_over`; GBDT fallback if XGB is missing |

Rate model always runs. Savant/XGB/calibration are overlays. A scrape or fit miss does not kill the card. Each prop carries `engine` (`rate`, `rate+savant`, `rate+savant+xgb`).

```bash
python3 -m pip install -r requirements.txt
python3 python/build_day.py --phase auto
python3 python/export_feed.py
python3 python/test_build_day.py
python3 python/test_stack.py
python3 python/train_models.py --min-rows 40
```

Morning phase refreshes FanGraphs tables. Grade phase appends `feed/history.jsonl` and fits when the sample clears 40 rows.

This is still a projection desk. No fake AUC.
