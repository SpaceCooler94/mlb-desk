#!/usr/bin/env python3
"""Offline unit tests for slate parse + phase clock. No network."""

from __future__ import annotations

import unittest
from datetime import date, datetime
from zoneinfo import ZoneInfo

import build_day as b
from props import PA_BY_SLOT, half_line, play

CT = ZoneInfo("America/Chicago")


class TestHelpers(unittest.TestCase):
    def test_half_line(self):
        self.assertEqual(half_line(6.0), 5.5)
        self.assertEqual(half_line(6.2), 6.5)
        self.assertEqual(half_line(5.4), 5.5)

    def test_play_dead_zone(self):
        self.assertEqual(play(5.6, 5.5, "k"), "PASS")
        self.assertEqual(play(6.6, 5.5, "k"), "WATCH")
        self.assertEqual(play(0.12, 0.5, "hr"), "PASS")
        self.assertEqual(play(0.32, 0.5, "hr"), "WATCH")

    def test_abbr_arizona(self):
        self.assertEqual(b._abbr({"abbreviation": "AZ"}), "ARI")
        self.assertEqual(b._abbr({"abbreviation": "ATH"}), "ATH")
        self.assertEqual(b._abbr({"abbreviation": "CWS"}), "CWS")

    def test_when_final_and_delay(self):
        self.assertIn("FINAL", b._when("2026-09-23T17:10:00Z", "Final"))
        self.assertIn("DELAY", b._when("2026-09-23T17:10:00Z", "Rain Delay"))

    def test_parse_date_grade_before_dawn(self):
        now = datetime(2026, 9, 24, 1, 30, tzinfo=CT)
        self.assertEqual(b.parse_date(None, "grade", now), date(2026, 9, 23))
        self.assertEqual(b.parse_date(None, "morning", now), date(2026, 9, 24))

    def test_auto_phase(self):
        self.assertEqual(b.auto_phase(datetime(2026, 9, 23, 8, 0, tzinfo=CT)), "morning")
        self.assertEqual(b.auto_phase(datetime(2026, 9, 23, 11, 45, tzinfo=CT)), "noon")
        self.assertEqual(b.auto_phase(datetime(2026, 9, 23, 18, 40, tzinfo=CT)), "lock")
        self.assertEqual(b.auto_phase(datetime(2026, 9, 23, 23, 10, tzinfo=CT)), "grade")

    def test_slot_encoding(self):
        self.assertEqual(b._slot(100), 1)
        self.assertEqual(b._slot(600), 6)
        self.assertEqual(b._slot(3), 3)
        self.assertIsNone(b._slot(0))

    def test_parse_games_contract(self):
        board = {
            "dates": [{
                "date": "2026-09-23",
                "games": [{
                    "gamePk": 1,
                    "gameDate": "2026-09-23T23:05:00Z",
                    "status": {"detailedState": "Pre-Game", "abstractGameState": "Preview"},
                    "venue": {"id": 3313, "name": "Yankee Stadium"},
                    "weather": {"condition": "Clear", "temp": "68"},
                    "lineups": {
                        "awayPlayers": [{"id": 10, "fullName": "Jose Caballero", "battingOrder": 100, "position": {"abbreviation": "SS"}}],
                        "homePlayers": [{"id": 20, "fullName": "Aaron Judge", "battingOrder": 200, "position": {"abbreviation": "RF"}}],
                    },
                    "teams": {
                        "away": {"team": {"abbreviation": "TB"}, "probablePitcher": {"id": 1, "fullName": "Mason Englert"}},
                        "home": {"team": {"abbreviation": "NYY"}, "probablePitcher": {"id": 2, "fullName": "Gerrit Cole"}},
                    },
                }],
            }]
        }
        games = b.parse_games(board)
        self.assertEqual(len(games), 1)
        g = games[0]
        self.assertEqual(g["id"], "2026-09-23_TB_NYY_1")
        self.assertEqual(g["park"], "Yankee Stadium")
        self.assertEqual(g["away_sp"], "Mason Englert")
        self.assertEqual(g["home_sp"], "Gerrit Cole")
        self.assertTrue(g["when"].startswith("Wed"))
        self.assertEqual(g["lineup_tag"], "CONFIRMED")
        self.assertEqual(g["home_lineup"][0]["name"], "Aaron Judge")
        self.assertEqual(g["home_lineup"][0]["slot"], 2)

    def test_lineup_without_batting_order_uses_list_index(self):
        players = [
            {"id": 1, "fullName": "Lead", "primaryPosition": {"abbreviation": "CF"}},
            {"id": 2, "fullName": "Two", "primaryPosition": {"abbreviation": "SS"}},
        ]
        rows = b._lineup_side(players)
        self.assertEqual([r["slot"] for r in rows], [1, 2])
        self.assertEqual(rows[0]["pos"], "CF")

    def test_project_hitter_park(self):
        prof = {"avg": 0.280, "slg": 0.560, "hr_pa": 0.055}
        coors = b.project_hitter(prof, 3, 19, 5.4)
        petco = b.project_hitter(prof, 3, 2680, 2.8)
        self.assertGreater(coors["hr"], petco["hr"])
        self.assertGreater(coors["hits"], petco["hits"])
        self.assertIn(3, PA_BY_SLOT)

    def test_doubleheader_ids_unique(self):
        def game(pk):
            return {
                "gamePk": pk,
                "gameDate": "2026-09-23T22:35:00Z",
                "status": {"detailedState": "Pre-Game", "abstractGameState": "Preview"},
                "venue": {"id": 2, "name": "Oriole Park at Camden Yards"},
                "teams": {
                    "away": {"team": {"abbreviation": "TOR"}, "probablePitcher": {"id": 1, "fullName": "A"}},
                    "home": {"team": {"abbreviation": "BAL"}, "probablePitcher": {"id": 2, "fullName": "B"}},
                },
            }
        board = {"dates": [{"date": "2026-09-23", "games": [game(111), game(222)]}]}
        games = b.parse_games(board)
        self.assertEqual({g["id"] for g in games}, {"2026-09-23_TOR_BAL_111", "2026-09-23_TOR_BAL_222"})

    def test_status_noon_live(self):
        games = [
            {"away_sp": "A", "home_sp": "B", "when": "Wed 6:05p"},
            {"away_sp": "C", "home_sp": "D", "when": "Wed 6:40p"},
        ]
        self.assertEqual(b.status_for("noon", games, []), "LIVE")
        games[0]["home_sp"] = "TBD"
        games[1]["home_sp"] = "TBD"
        self.assertEqual(b.status_for("noon", games, []), "SEED_PRIOR")
        self.assertEqual(b.status_for("lock", games, []), "LOCKED")


if __name__ == "__main__":
    unittest.main()
