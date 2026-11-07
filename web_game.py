"""Loopback-only web adapter over the existing RPG callbacks and SQLite save."""
import asyncio
import json
import secrets
import shlex
import sqlite3
import webbrowser
from pathlib import Path
from types import SimpleNamespace
from contextlib import contextmanager

from aiohttp import web
from discord.ext import commands

import bot as game
from autoplay import Pilot
from text_commands import parse_arguments

ROOT = Path(__file__).resolve().parent
CATEGORIES = {
    "Personnage": "commencer profil inventaire niveau_max succes classement aide",
    "Aventure": "hunt aventure chasse quete boss regions bestiary chasser_region statistiques_chasse",
    "Quêtes": "quetes reclamer_quete quotidien",
    "Métiers": "metiers exercer recolter mine couper peche travail",
    "Atelier": "crafts fabriquer equipements equiper porter",
    "Marché": "boutique acheter vendre",
    "Écurie": "chevaux acheter_cheval entrainer_cheval",
    "Donjons": "donjons entrer_donjon avancer_donjon quitter_donjon",
    "Soins": "utiliser repos",
}


class Reply:
    _web_reply = True

    def __init__(self, uid):
        self.user = SimpleNamespace(id=uid, display_name="Aventurier")
        self.response = self
        self.messages = []

    async def send_message(self, text, **kwargs):
        self.messages.append(text)


@contextmanager
def connect():
    # mode=rw deliberately refuses to create a new save by accident.
    db = sqlite3.connect(Path(game.DB).resolve().as_uri()+"?mode=rw", uri=True, timeout=15)
    db.row_factory = sqlite3.Row
    try:
        yield db
    finally:
        db.close()


def players():
    with connect() as db:
        rows = db.execute("SELECT id,level,gold,wins FROM players ORDER BY level DESC").fetchall()
    return [dict(r, id=str(r["id"])) for r in rows
            if not game.OWNER_ID or r["id"] == game.OWNER_ID]


def snapshot(uid):
    with connect() as db:
        p = db.execute("SELECT * FROM players WHERE id=?", (uid,)).fetchone()
        if p is None:
            raise web.HTTPConflict(text="Personnage introuvable dans cette sauvegarde.")
        inventory = [dict(r) for r in db.execute(
            "SELECT item,qty FROM inventory WHERE user_id=? AND qty>0 ORDER BY item", (uid,))]
        cooldowns = dict(db.execute("SELECT action,until_at FROM cooldowns WHERE user_id=?", (uid,)))
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        equipment = {}
        if "equipment" in tables:
            row = db.execute("SELECT weapon,armor FROM equipment WHERE user_id=?", (uid,)).fetchone()
            if row:
                equipment = dict(row)
        if "boss_timers" in tables:
            row = db.execute("SELECT ready_at FROM boss_timers WHERE user_id=?", (uid,)).fetchone()
            if row:
                cooldowns["boss"] = row[0]
        if "job_cooldowns" in tables:
            cooldowns.update(dict(db.execute(
                "SELECT job,until_at FROM job_cooldowns WHERE user_id=?", (uid,))))
    return {"player": dict(p, id=str(p["id"])), "inventory": inventory,
            "cooldowns": cooldowns, "equipment": equipment}


def catalogue():
    result = []
    for command in game.bot.tree.get_commands():
        category = next((name for name, names in CATEGORIES.items()
                         if command.name in names.split()), "Autres")
        parameters = []
        for p in command.parameters:
            options = [{"value": c.value, "label": c.name} for c in p.choices]
            if not options and p.name == "objet":
                keys = (game.RECIPES if command.name == "fabriquer" else
                        game.progression_extension.GEAR if command.name == "porter" else
                        ["epee", "armure"] if command.name == "equiper" else
                        ["potion", "grande_potion"] if command.name == "utiliser" else game.ITEMS)
                options = [{"value": key, "label": game.ITEMS.get(key, (key, 0))[0]} for key in keys
                           if not (command.name == "porter" and key == "elixir")]
            if p.name == "nom" and command.name == "acheter_cheval":
                options = [{"value": k, "label": k.replace("_", " ").title()} for k in game.HORSES]
            if p.name == "nom" and command.name == "reclamer_quete":
                options = [{"value": q[0], "label": q[0]} for q in game.progression_extension.QUESTS]
            parameters.append({"name": p.name, "required": p.required,
                               "default": p.default if not p.required else None,
                               "type": p.type.name, "min": p.min_value, "max": p.max_value,
                               "options": options})
        result.append({"name": command.name, "description": command.description,
                       "category": category, "parameters": parameters})
    return result


def create_app():
    csrf = secrets.token_urlsafe(32)
    sessions = {}
    lock = asyncio.Lock()
    pilot = Pilot(snapshot, connect, Reply, lock)
    port = 8765

    @web.middleware
    async def local_only(request, handler):
        if request.host != f"127.0.0.1:{port}":
            raise web.HTTPForbidden(text="Interface locale uniquement.")
        if request.method == "POST":
            if request.headers.get("Origin") != f"http://127.0.0.1:{port}":
                raise web.HTTPForbidden()
            if request.headers.get("X-Game-Session") != csrf:
                raise web.HTTPForbidden()
        try:
            return await handler(request)
        except (commands.BadArgument, ValueError, TypeError, KeyError, json.JSONDecodeError):
            return web.json_response({"error": "Paramètres invalides. Vérifie les champs."}, status=400)
        except sqlite3.Error:
            return web.json_response({"error": "Sauvegarde indisponible. Vérifie le dossier du jeu et réessaie."}, status=503)

    app = web.Application(middlewares=[local_only], client_max_size=8192)

    def selected(request):
        uid = sessions.get(request.cookies.get("rpg_session", ""))
        if uid is None or (game.OWNER_ID and uid != game.OWNER_ID):
            raise web.HTTPUnauthorized(text="Choisis ton personnage.")
        return uid

    async def bootstrap(request):
        return web.json_response({"csrf": csrf, "players": players(),
                                 "commands": catalogue(), "items": game.ITEMS,
                                 "save": Path(game.DB).name})

    async def select(request):
        data = await request.json()
        uid = str(data.get("id", ""))
        if uid not in {p["id"] for p in players()}:
            raise web.HTTPForbidden()
        await pilot.stop("Arrêt : changement de personnage.")
        session = secrets.token_urlsafe(32)
        sessions.clear()  # one local player at a time
        sessions[session] = int(uid)
        response = web.json_response(snapshot(int(uid)))
        response.set_cookie("rpg_session", session, httponly=True, samesite="Strict")
        return response

    async def state(request):
        return web.json_response(snapshot(selected(request)))

    async def execute(request):
        uid = selected(request)
        data = await request.json()
        command = game.bot.tree.get_command(str(data.get("command", "")))
        if command is None:
            raise web.HTTPNotFound()
        args = data.get("args", {})
        if not isinstance(args, dict) or set(args)-{p.name for p in command.parameters}:
            raise ValueError()
        words = []
        for p in command.parameters:
            value = args.get(p.name, p.default if not p.required else None)
            if value is None or str(value).strip() == "":
                if p.required:
                    raise commands.BadArgument()
                value = p.default
            words.append(shlex.quote(str(value)))
        values = parse_arguments(command, " ".join(words))
        if pilot.active:
            await pilot.stop("Arrêt : tu reprends le contrôle manuellement.")
        async with lock:
            snapshot(uid)  # never let callbacks silently create a missing character
            reply = Reply(uid)
            await command.callback(reply, **values)
            return web.json_response({"messages": reply.messages, "state": snapshot(uid)})

    async def index(request):
        return web.FileResponse(ROOT / "web" / "index.html")

    async def auto_status(request):
        uid = selected(request)
        status = pilot.status()
        if pilot.uid != uid:
            status = {"active": False, "reason": "Prêt à démarrer.", "events": [],
                      "spent": 0, "budget": 0, "ends_at": 0, "player_id": str(uid)}
        return web.json_response(status)

    async def auto_start(request):
        uid = selected(request)
        data = await request.json()
        pilot.start(uid, data.get("minutes", 60), data.get("budget", 150))
        return web.json_response(pilot.status())

    async def auto_stop(request):
        selected(request)
        await pilot.stop()
        return web.json_response(pilot.status())

    async def cleanup(app):
        await pilot.stop("Arrêt du programme.")

    app.on_cleanup.append(cleanup)

    app.router.add_get("/", index)
    app.router.add_get("/api/bootstrap", bootstrap)
    app.router.add_post("/api/select", select)
    app.router.add_get("/api/state", state)
    app.router.add_post("/api/action", execute)
    app.router.add_get("/api/auto", auto_status)
    app.router.add_post("/api/auto/start", auto_start)
    app.router.add_post("/api/auto/stop", auto_stop)
    app.router.add_static("/assets/", ROOT / "web")
    return app


def main():
    if not Path(game.DB).is_file():
        raise SystemExit("Sauvegarde introuvable. Copie ces fichiers dans le dossier habituel du bot, avec adventure.db.")
    try:
        existing = players()
    except sqlite3.Error:
        raise SystemExit("Cette base ne contient pas la sauvegarde du jeu. Vérifie DATABASE_PATH dans ton .env.")
    if not existing:
        raise SystemExit("Aucun personnage existant autorisé. Vérifie OWNER_ID et ta sauvegarde.")
    print(f"Sauvegarde utilisée : {Path(game.DB).resolve()}")
    print("Ouvre http://127.0.0.1:8765 — garde cette fenêtre ouverte. Ctrl+C pour arrêter.")
    webbrowser.open("http://127.0.0.1:8765")
    web.run_app(create_app(), host="127.0.0.1", port=8765, print=None)


if __name__ == "__main__":
    raise SystemExit("Lance plutôt : py start_web.py")
