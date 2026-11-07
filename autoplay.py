"""Autonomous local strategy; no LLM, external service or Discord login."""
import asyncio
import math
import sqlite3
import time
from pathlib import Path
from datetime import datetime, timezone

import bot as game


def plan(state, now, spent, budget):
    p = state["player"]
    inventory = {r["item"]: r["qty"] for r in state["inventory"]}
    if p["hp"] <= 0:
        return {"stop": "Personnage KO : reprise manuelle nécessaire."}
    if p["dungeon"]:
        return {"stop": "Un donjon est en cours : termine-le ou quitte-le manuellement."}
    if p["level"] >= 100:
        return {"stop": "Objectif atteint : niveau 100."}
    if p["hp"] < p["max_hp"] * .8:
        for item in ("grande_potion", "potion"):
            if inventory.get(item, 0):
                return {"command": "utiliser", "args": {"objet": item}, "reason": "Récupérer des PV avant de repartir."}
        if p["gold"] >= 15 and spent + 15 <= budget:
            return {"command": "repos", "args": {}, "cost": 15, "reason": "Se soigner contre 15 pièces."}
        return {"stop": "Soins indisponibles ou budget de repos atteint."}
    today = datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d")
    if p["last_daily"] != today:
        return {"command": "quotidien", "args": {}, "reason": "Récupérer la récompense quotidienne."}
    for quest in state.get("ready_quests", []):
        return {"command": "reclamer_quete", "args": {"nom": quest}, "reason": "Une quête terminée attend sa récompense."}
    # Wear only already-owned gear with strictly better bonuses.
    gear = game.progression_extension.GEAR
    for item, (_, _, atk, defense, hp) in sorted(gear.items(),
            key=lambda pair: sum(pair[1][2:]), reverse=True):
        if item == "elixir" or not inventory.get(item, 0):
            continue
        slot = "weapon" if atk else "armor"
        old = gear.get(state["equipment"].get(slot), ({}, 0, 0, 0, 0))
        if atk >= old[2] and defense >= old[3] and hp >= old[4] and (atk, defense, hp) != tuple(old[2:]):
            return {"command": "porter", "args": {"objet": item}, "reason": "Porter un équipement possédé avec de meilleurs bonus."}
    for item in ("epee", "armure"):
        if inventory.get(item, 0):
            return {"command": "equiper", "args": {"objet": item}, "reason": "Utiliser une amélioration permanente déjà possédée."}
    timers = state["cooldowns"]
    biome = [b for b in game.progression_extension.BIOMES if p["level"] >= b[1]][-1]
    tier = min(len(game.MONSTERS)-1, max(0, (p["level"]-1)//5))
    classic = game.MONSTERS[max(0, tier-1):tier+1]

    def acceptable(monsters):
        attack = max(1, p["atk"] + game.horse_bonus(p) - 6)
        for _, hp, damage, *_ in monsters:
            rounds = math.ceil(hp / attack)
            # Conservative estimate, not a guarantee of survival.
            loss = max(0, rounds-1) * max(1, damage+4-p["defense"]//2)
            if rounds > 40 or loss + p["max_hp"]*.15 >= p["hp"]:
                return False
        return True

    if timers.get("chasse", 0) <= now:
        if acceptable(biome[2]):
            return {"command": "hunt", "args": {}, "reason": "Chasser dans la zone actuelle ; risque estimé acceptable."}
        if acceptable(classic):
            return {"command": "chasse", "args": {}, "reason": "Choisir une chasse classique plus accessible."}
    for item, timer in (("fer", "mine"), ("bois", "couper"), ("poisson", "peche")):
        if timers.get(timer, 0) <= now:
            return {"command": "recolter", "args": {"metier": item},
                    "reason": "Récolter et gagner de l'expérience pendant la préparation du prochain combat."}
    if timers.get("travail", 0) <= now:
        return {"command": "travail", "args": {}, "reason": "Gagner de l'or pendant les délais d'attente."}
    return {"wait": True, "reason": "Attente des délais du jeu."}


class Pilot:
    def __init__(self, read_state, connection, reply_factory, lock):
        self.read_state = read_state
        self.connection = connection
        self.reply_factory = reply_factory
        self.lock = lock
        self.task = None
        self.uid = None
        self.active = False
        self.reason = "Prêt à démarrer."
        self.events = []
        self.sequence = 0
        self.spent = 0
        self.budget = 0
        self.ends_at = 0

    def status(self):
        return {"active": self.active, "reason": self.reason, "spent": self.spent,
                "budget": self.budget, "ends_at": self.ends_at,
                "player_id": str(self.uid) if self.uid is not None else None,
                "events": self.events}

    def event(self, command, messages):
        self.sequence += 1
        self.events.append({"id": self.sequence, "command": command, "messages": messages})
        self.events = self.events[-50:]

    def start(self, uid, minutes, budget):
        if self.active:
            raise ValueError("Déjà actif")
        if type(minutes) is not int or not 1 <= minutes <= 1440:
            raise ValueError("Durée invalide")
        if type(budget) is not int or not 0 <= budget <= 100000:
            raise ValueError("Budget invalide")
        self.uid = uid
        self.read_state(uid)
        backup_dir = Path(game.DB).resolve().parent / "backups"
        backup_dir.mkdir(exist_ok=True)
        backup_path = backup_dir / f"avant_auto_{time.time_ns()}.db"
        with self.connection() as source:
            target = sqlite3.connect(backup_path)
            try:
                source.backup(target)
            finally:
                target.close()
        self.spent, self.budget = 0, budget
        self.ends_at = time.time() + minutes*60
        self.active = True
        self.reason = "Progression automatique en cours."
        self.event("auto", [f"Programme démarré pour {minutes} minutes. Budget de repos : {budget} pièces.",
                            f"Copie de sauvegarde créée : backups/{backup_path.name}"])
        self.task = asyncio.create_task(self.run())

    async def stop(self, reason="Arrêt demandé."):
        was_active = self.active
        self.active = False
        if self.task and self.task is not asyncio.current_task():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        self.task = None
        self.reason = reason
        if was_active:
            self.event("auto", [reason])

    def view(self):
        state = self.read_state(self.uid)
        with self.connection() as db:
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if {"counters", "quest_claims"} <= tables:
                counters = dict(db.execute("SELECT action,value FROM counters WHERE user_id=?", (self.uid,)))
                claimed = {r[0] for r in db.execute("SELECT quest FROM quest_claims WHERE user_id=?", (self.uid,))}
                state["ready_quests"] = [name for name, action, target, *_ in game.progression_extension.QUESTS
                                         if name not in claimed and counters.get(action, 0) >= target]
        return state

    async def step(self, now=None):
        now = time.time() if now is None else now
        async with self.lock:
            if not self.active:
                return
            if now >= self.ends_at:
                await self.stop("Durée choisie terminée.")
                return
            if game.OWNER_ID and self.uid != game.OWNER_ID:
                await self.stop("Ce personnage n'est plus autorisé.")
                return
            decision = plan(self.view(), now, self.spent, self.budget)
            if "stop" in decision:
                await self.stop(decision["stop"])
                return
            self.reason = decision["reason"]
            if decision.get("wait"):
                return
            from text_commands import parse_arguments
            import shlex
            command = game.bot.tree.get_command(decision["command"])
            args = parse_arguments(command, " ".join(shlex.quote(str(v)) for v in decision["args"].values()))
            reply = self.reply_factory(self.uid)
            await command.callback(reply, **args)
            self.spent += decision.get("cost", 0)
            self.event(command.name, [self.reason, *reply.messages])

    async def run(self):
        try:
            while self.active:
                await self.step()
                await asyncio.sleep(2)
        except asyncio.CancelledError:
            raise
        except Exception:
            self.active = False
            self.reason = "Programme arrêté après une erreur. Vérifie la sauvegarde puis redémarre."
            self.event("auto", [self.reason])
