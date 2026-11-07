import asyncio
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

import bot as game
from autoplay import Pilot, plan
from web_game import snapshot, connect, Reply


def finish(coro):
    try:
        coro.send(None)
    except StopIteration as result:
        return result.value
    raise AssertionError("Unexpected external I/O")


class AutoPlayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.previous = game.DB, game.OWNER_ID
        game.DB = str(Path(self.temp.name) / "auto.db")
        game.OWNER_ID = 0
        game.init_db()
        self.now = time.time()
        with game.connection() as db:
            game.player(db, 123)
            game.change(db, 123, atk=500, max_hp=500, hp=500, gold=1000,
                        last_daily=datetime.now(timezone.utc).strftime("%Y-%m-%d"))

    def tearDown(self):
        game.DB, game.OWNER_ID = self.previous
        self.temp.cleanup()

    def test_stop_and_healing_budget(self):
        s = snapshot(123)
        s["player"]["hp"] = 0
        self.assertIn("stop", plan(s, self.now, 0, 150))
        s["player"]["hp"] = 50
        self.assertEqual(plan(s, self.now, 0, 15)["command"], "repos")
        self.assertIn("stop", plan(s, self.now, 15, 15))
        s["inventory"] = [{"item": "potion", "qty": 1}]
        self.assertEqual(plan(s, self.now, 15, 15)["command"], "utiliser")
        s["player"]["dungeon"] = 1
        self.assertIn("stop", plan(s, self.now, 0, 150))

    def test_decisions_and_cooldowns(self):
        s = snapshot(123)
        self.assertEqual(plan(s, self.now, 0, 0)["command"], "hunt")
        s["cooldowns"]["chasse"] = self.now + 30
        self.assertEqual(plan(s, self.now, 0, 0)["command"], "recolter")
        for action in ("mine", "couper", "peche", "travail"):
            s["cooldowns"][action] = self.now + 60
        self.assertTrue(plan(s, self.now, 0, 0)["wait"])
        s["ready_quests"] = ["Chasseur novice"]
        self.assertEqual(plan(s, self.now, 0, 0)["command"], "reclamer_quete")

    def test_live_step_and_stop(self):
        pilot = Pilot(snapshot, connect, Reply, asyncio.Lock())
        pilot.uid, pilot.active, pilot.ends_at = 123, True, self.now + 600
        finish(pilot.step(self.now))
        self.assertEqual(pilot.events[-1]["command"], "hunt")
        finish(pilot.step(self.now + 2))
        self.assertEqual(pilot.events[-1]["command"], "recolter")
        count = len(pilot.events)
        finish(pilot.stop())
        finish(pilot.step(self.now + 4))
        self.assertEqual(len(pilot.events), count+1)
        self.assertFalse(pilot.active)

    def test_expiration_and_foreign_owner(self):
        pilot = Pilot(snapshot, connect, Reply, asyncio.Lock())
        pilot.uid, pilot.active, pilot.ends_at = 123, True, self.now-1
        finish(pilot.step(self.now))
        self.assertFalse(pilot.active)
        pilot.active, pilot.ends_at = True, self.now+60
        game.OWNER_ID = 456
        finish(pilot.step(self.now))
        self.assertFalse(pilot.active)


if __name__ == "__main__":
    unittest.main()
