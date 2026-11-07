"""Offline tests: no Discord login, browser or real save is used."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from aiohttp import web
import bot as game
from web_game import create_app, catalogue, connect, players, snapshot


def finish(coro):
    # These handlers await only local, immediately-completed game callbacks.
    try:
        coro.send(None)
    except StopIteration as result:
        return result.value
    raise AssertionError("Unexpected external I/O in offline test")


class Request:
    host = "127.0.0.1:8765"
    method = "GET"
    headers = {}
    cookies = {}

    def __init__(self, data=None, cookie=None, csrf=None):
        self.data = data
        self.cookies = {"rpg_session": cookie} if cookie else {}
        self.headers = {"Origin": "http://127.0.0.1:8765", "X-Game-Session": csrf or ""}
        self.method = "POST" if data is not None else "GET"

    async def json(self):
        return self.data


class WebGameTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.previous = game.DB, game.OWNER_ID
        game.DB = str(Path(self.temp.name) / "save.db")
        game.OWNER_ID = 0
        game.init_db()
        with game.connection() as db:
            game.player(db, 123)
            game.player(db, 456)
            game.change(db, 123, level=100, gold=100000, hp=2000, max_hp=2000, atk=500)
            for key in game.ITEMS:
                game.give(db, 123, key, 50)
        self.app = create_app()
        self.routes = {r.resource.canonical: r.handler for r in self.app.router.routes()}

    def tearDown(self):
        game.DB, game.OWNER_ID = self.previous
        self.temp.cleanup()

    def call(self, path, data=None, cookie=None, csrf=None):
        request = Request(data, cookie, csrf)
        response = finish(self.app.middlewares[0](request, self.routes[path]))
        return response, json.loads(response.body)

    def login(self):
        _, data = self.call("/api/bootstrap")
        response, state = self.call("/api/select", {"id": "123"}, csrf=data["csrf"])
        return data["csrf"], response.cookies["rpg_session"].value

    def test_read_only_bootstrap_and_no_missing_save_creation(self):
        before = Path(game.DB).read_bytes()
        _, data = self.call("/api/bootstrap")
        self.assertEqual(len(data["commands"]), len(game.bot.tree.get_commands()))
        self.assertEqual(before, Path(game.DB).read_bytes())
        game.DB = str(Path(self.temp.name) / "missing.db")
        with self.assertRaises(Exception):
            with connect():
                pass
        self.assertFalse(Path(game.DB).exists())

    def test_all_commands_execute_against_shared_save(self):
        csrf, cookie = self.login()
        for command in catalogue():
            args = {}
            for p in command["parameters"]:
                if p["options"]:
                    args[p["name"]] = p["options"][0]["value"]
                elif p["type"] == "integer":
                    args[p["name"]] = p["min"] or 1
                elif p["required"]:
                    args[p["name"]] = "armure"
            with self.subTest(command=command["name"]):
                response, result = self.call("/api/action", {"command": command["name"], "args": args}, cookie, csrf)
                self.assertEqual(response.status, 200, result)
                self.assertTrue(result["messages"])
                self.assertEqual(result["state"]["player"]["id"], "123")
        self.assertEqual(snapshot(123)["player"]["id"], "123")
        self.assertEqual(len(players()), 2)

    def test_invalid_input_and_browser_guards(self):
        csrf, cookie = self.login()
        for args in [{"objet": "potion", "quantite": -1}, {"objet": "potion", "quantite": 101}]:
            before = snapshot(123)
            response, _ = self.call("/api/action", {"command": "acheter", "args": args}, cookie, csrf)
            self.assertEqual(response.status, 400)
            self.assertEqual(snapshot(123), before)
        with self.assertRaises(web.HTTPForbidden):
            self.call("/api/action", {"command": "hunt"}, cookie, "wrong")
        request = Request()
        request.host = "other.example:8765"
        with self.assertRaises(web.HTTPForbidden):
            finish(self.app.middlewares[0](request, self.routes["/api/bootstrap"]))
        with self.assertRaises(web.HTTPUnauthorized):
            self.call("/api/state")
        game.OWNER_ID = 456
        self.assertEqual([p["id"] for p in players()], ["456"])
        with self.assertRaises(web.HTTPUnauthorized):
            self.call("/api/state", cookie=cookie)


if __name__ == "__main__":
    unittest.main()
