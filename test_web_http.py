"""Real HTTP integration checks, run by GitHub Actions."""
import tempfile
import unittest
from pathlib import Path

from aiohttp.test_utils import TestClient, TestServer
import bot as game
from web_game import create_app


class WebHttpTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.previous = game.DB, game.OWNER_ID
        game.DB = str(Path(self.temp.name) / "http.db")
        game.OWNER_ID = 0
        game.init_db()
        with game.connection() as db:
            game.player(db, 123)
        self.client = TestClient(TestServer(create_app()))
        await self.client.start_server()
        self.headers = {"Host": "127.0.0.1:8765", "Origin": "http://127.0.0.1:8765"}

    async def asyncTearDown(self):
        await self.client.close()
        game.DB, game.OWNER_ID = self.previous
        self.temp.cleanup()

    async def test_page_login_action_and_shared_cooldown(self):
        response = await self.client.get("/", headers=self.headers)
        self.assertEqual(response.status, 200)
        self.assertIn("Journal d'aventure", await response.text())
        for asset in ["app.js", "style.css", "world.svg"]:
            response = await self.client.get("/assets/"+asset, headers=self.headers)
            self.assertEqual(response.status, 200)
        response = await self.client.get("/api/bootstrap", headers=self.headers)
        data = await response.json()
        self.headers["X-Game-Session"] = data["csrf"]
        response = await self.client.post("/api/select", headers=self.headers, json={"id": "123"})
        self.assertEqual(response.status, 200)
        self.headers["Cookie"] = "rpg_session="+response.cookies["rpg_session"].value
        for _ in range(2):
            response = await self.client.post("/api/action", headers=self.headers,
                                              json={"command": "mine", "args": {}})
            self.assertEqual(response.status, 200)
            data = await response.json()
        self.assertIn("Patiente", data["messages"][0])
        self.assertTrue(data["state"]["inventory"])
        response = await self.client.post("/api/action",
            headers={**self.headers, "Origin": "https://other.example"},
            json={"command": "hunt"})
        self.assertEqual(response.status, 403)
        response = await self.client.get("/assets/../.env", headers=self.headers)
        self.assertEqual(response.status, 404)

    async def test_autoplay_start_stop_and_auth(self):
        response = await self.client.post("/api/auto/start", headers=self.headers,
                                           json={"minutes": 1, "budget": 0})
        self.assertEqual(response.status, 403)
        response = await self.client.get("/api/bootstrap", headers=self.headers)
        data = await response.json()
        self.headers["X-Game-Session"] = data["csrf"]
        response = await self.client.post("/api/select", headers=self.headers, json={"id": "123"})
        self.headers["Cookie"] = "rpg_session="+response.cookies["rpg_session"].value
        response = await self.client.post("/api/auto/start", headers=self.headers,
                                           json={"minutes": 1, "budget": 0})
        self.assertEqual(response.status, 200)
        self.assertTrue((await response.json())["active"])
        response = await self.client.post("/api/auto/stop", headers=self.headers, json={})
        self.assertEqual(response.status, 200)
        self.assertFalse((await response.json())["active"])
        response = await self.client.post("/api/auto/start", headers=self.headers,
                                           json={"minutes": -1, "budget": 0})
        self.assertEqual(response.status, 400)


if __name__ == "__main__":
    unittest.main()
