"""EPIC Adventure Solo — bot Discord RPG solo, sauvegarde SQLite."""
import asyncio
import json
import os
import random
import sqlite3
import time
from contextlib import contextmanager

import discord
from discord import app_commands
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN", "")
DB = os.getenv("DATABASE_PATH", "adventure.db")
GUILD_ID = os.getenv("GUILD_ID", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0") or 0)
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="rpg ", intents=intents, help_command=None)

MONSTERS = [
    ("Slime", 18, 3, 8, 8), ("Loup", 35, 6, 13, 14),
    ("Gobelin", 60, 9, 20, 24), ("Squelette", 90, 13, 29, 38),
    ("Golem", 135, 18, 44, 60), ("Dragonnet", 200, 25, 68, 90),
]
DUNGEONS = [
    ("Grotte oubliée", 1, 3), ("Forêt maudite", 5, 4),
    ("Crypte ancienne", 10, 5), ("Forteresse noire", 15, 6),
    ("Temple céleste", 20, 7), ("Antre du dragon", 30, 8),
]
ITEMS = {
    "potion": ("Potion de soin", 25),
    "grande_potion": ("Grande potion", 70),
    "epee": ("Épée renforcée", 120),
    "armure": ("Armure renforcée", 150),
    "fer": ("Minerai de fer", 15),
    "bois": ("Bois", 10),
    "poisson": ("Poisson", 12),
    "cristal": ("Cristal", 90),
}
HORSES = {
    "poney": (100, 2), "destrier": (600, 5),
    "pur_sang": (2000, 10), "spectral": (8000, 18),
}
RECIPES = {
    "epee": ({"fer": 5, "bois": 2}, 50),
    "armure": ({"fer": 8}, 75),
    "grande_potion": ({"poisson": 3, "cristal": 1}, 30),
}
COOLDOWNS = {"aventure": 45, "chasse": 30, "mine": 45, "couper": 45,
             "peche": 45, "travail": 60, "quete": 90, "donjon": 120}

@contextmanager
def connection():
    con = sqlite3.connect(DB, timeout=15)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()

def init_db():
    with connection() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS players(
          id INTEGER PRIMARY KEY, level INTEGER DEFAULT 1,
          xp INTEGER DEFAULT 0, gold INTEGER DEFAULT 100,
          hp INTEGER DEFAULT 100, max_hp INTEGER DEFAULT 100,
          atk INTEGER DEFAULT 10, defense INTEGER DEFAULT 3,
          wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0,
          horse TEXT DEFAULT '', horse_level INTEGER DEFAULT 1,
          dungeon INTEGER DEFAULT 0, dungeon_floor INTEGER DEFAULT 0,
          last_daily TEXT DEFAULT '', created INTEGER DEFAULT 0)""")
        db.execute("""CREATE TABLE IF NOT EXISTS inventory(
          user_id INTEGER, item TEXT, qty INTEGER DEFAULT 0,
          PRIMARY KEY(user_id,item))""")
        db.execute("""CREATE TABLE IF NOT EXISTS cooldowns(
          user_id INTEGER, action TEXT, until_at INTEGER,
          PRIMARY KEY(user_id,action))""")
        db.execute("""CREATE TABLE IF NOT EXISTS achievements(
          user_id INTEGER, achievement TEXT,
          PRIMARY KEY(user_id,achievement))""")

def player(db, uid):
    db.execute("INSERT OR IGNORE INTO players(id,created) VALUES(?,?)", (uid,int(time.time())))
    return db.execute("SELECT * FROM players WHERE id=?", (uid,)).fetchone()

def item_qty(db, uid, key):
    r=db.execute("SELECT qty FROM inventory WHERE user_id=? AND item=?", (uid,key)).fetchone()
    return r["qty"] if r else 0

def give(db, uid, key, qty):
    current=item_qty(db,uid,key)
    if current+qty<0:
        raise ValueError("Quantité insuffisante.")
    db.execute("""INSERT INTO inventory(user_id,item,qty) VALUES(?,?,?)
        ON CONFLICT(user_id,item) DO UPDATE SET qty=excluded.qty""",(uid,key,current+qty))

def change(db, uid, **values):
    if not values:
        return
    allowed={"xp","gold","hp","max_hp","atk","defense","wins","losses","horse","horse_level","dungeon","dungeon_floor","last_daily","level"}
    if any(k not in allowed for k in values):
        raise ValueError("Champ interdit")
    sql=", ".join(f"{k}=?" for k in values)
    db.execute(f"UPDATE players SET {sql} WHERE id=?",(*values.values(),uid))

def award(db, uid, xp=0, gold=0):
    p=player(db,uid)
    lvl=p["level"]
    total=p["xp"]+xp
    gained=0
    while lvl<100 and total>=lvl*75:
        total-=lvl*75
        lvl+=1
        gained+=1
    change(db,uid,xp=total,level=lvl,gold=max(0,p["gold"]+gold),
           max_hp=p["max_hp"]+gained*12,
           hp=min(p["max_hp"]+gained*12,p["hp"]+gained*12),
           atk=p["atk"]+gained*2,defense=p["defense"]+gained)
    return f"✨ +{xp} XP · 🪙 {gold:+} pièces"+(f" · ⬆️ Niveau {lvl} !" if gained else "")

def cooldown(db,uid,action):
    now=int(time.time())
    r=db.execute("SELECT until_at FROM cooldowns WHERE user_id=? AND action=?",(uid,action)).fetchone()
    if r and r["until_at"]>now:
        return r["until_at"]-now
    db.execute("""INSERT INTO cooldowns VALUES(?,?,?)
      ON CONFLICT(user_id,action) DO UPDATE SET until_at=excluded.until_at""",
      (uid,action,now+COOLDOWNS.get(action,30)))
    return 0

def horse_bonus(p):
    return HORSES.get(p["horse"],(0,0))[1]+max(0,p["horse_level"]-1) if p["horse"] else 0

def fight(p, monster, boss=False):
    name, base_hp, attack, xp, gold=monster
    enemy_hp=base_hp*(2 if boss else 1)
    hp=p["hp"]
    rounds=0
    log=[]
    while hp>0 and enemy_hp>0 and rounds<40:
        rounds+=1
        damage=max(1,p["atk"]+horse_bonus(p)+random.randint(-3,6)-random.randint(0,3))
        if random.random()<0.12:
            damage*=2
        enemy_hp-=damage
        if enemy_hp<=0:
            break
        incoming=max(1,attack+random.randint(-2,4)-p["defense"]//2)
        if random.random()<0.08:
            incoming=0
        hp-=incoming
        if rounds<=3:
            log.append(f"Tour {rounds} : -{damage} PV ennemi, -{incoming} PV joueur")
    return hp>0, max(0,hp), "\n".join(log), xp*(2 if boss else 1), gold*(2 if boss else 1)

async def respond(interaction, text, private=False):
    if isinstance(interaction, commands.Context):
        # Text commands have no ephemeral replies. Restricted replies go to DM.
        if private:
            try:
                await interaction.author.send(text[:1950])
            except discord.Forbidden:
                pass
        else:
            await interaction.send(text[:1950], allowed_mentions=discord.AllowedMentions.none())
        return
    await interaction.response.send_message(text[:1950],ephemeral=private)

async def authorized(interaction):
    if OWNER_ID and interaction.user.id!=OWNER_ID:
        await respond(interaction,"🔒 Ce bot est réservé à son propriétaire.",True)
        return False
    return True

@bot.tree.command(name="aide",description="Toutes les commandes du RPG")
async def aide(interaction:discord.Interaction):
    await respond(interaction,"""🏰 **EPIC ADVENTURE SOLO**
**Personnage :** /commencer /profil /inventaire /classement /repos
**Progression :** /aventure /chasse /quete /quotidien /travail
**Ressources :** /mine /couper /peche
**Économie :** /boutique /acheter /vendre /fabriquer
**Équipement :** /equiper /utiliser
**Chevaux :** /chevaux /acheter_cheval /entrainer_cheval
**Donjons solo :** /donjons /entrer_donjon /avancer_donjon /quitter_donjon
**Divers :** /succes /repos
**Extensions :** /hunt /boss /quetes /reclamer_quete /recolter /crafts /porter
**Niveau 100 :** /regions /bestiary /metiers /exercer /equipements /chasser_region /statistiques_chasse /niveau_max
Toutes ces commandes existent aussi avec le préfixe rpg suivi d'un espace.
Exemples : rpg hunt · rpg profil · rpg inventaire · rpg boss · rpg equiper armure
Toutes les données sont sauvegardées automatiquement.""")

@bot.tree.command(name="commencer",description="Créer son personnage")
async def commencer(interaction:discord.Interaction):
    if not await authorized(interaction):return
    with connection() as db:
        existed=db.execute("SELECT 1 FROM players WHERE id=?",(interaction.user.id,)).fetchone()
        player(db,interaction.user.id)
        if not existed:
            give(db,interaction.user.id,"potion",3)
    await respond(interaction,"🎉 Personnage prêt ! /profil pour voir tes statistiques." if not existed else "Ton personnage existe déjà. /profil")

@bot.tree.command(name="profil",description="Voir les statistiques de ton personnage")
async def profil(interaction:discord.Interaction):
    if not await authorized(interaction):return
    with connection() as db:
        p=player(db,interaction.user.id)
    await respond(interaction,f"""🧙 **{interaction.user.display_name}** · niveau **{p['level']}**
❤️ {p['hp']}/{p['max_hp']} PV · ⚔️ {p['atk']} attaque · 🛡️ {p['defense']} défense
✨ {p['xp']}/{p['level']*75} XP · 🪙 {p['gold']} pièces
🐴 {p['horse'] or 'Aucun'} (niveau {p['horse_level']})
🏆 {p['wins']} victoires · 💀 {p['losses']} défaites""")

@bot.tree.command(name="inventaire",description="Consulter ses objets")
async def inventaire(interaction:discord.Interaction):
    if not await authorized(interaction):return
    with connection() as db:
        player(db,interaction.user.id)
        rows=db.execute("SELECT item,qty FROM inventory WHERE user_id=? AND qty>0 ORDER BY item",(interaction.user.id,)).fetchall()
    await respond(interaction,"🎒 **Inventaire**\n"+("\n".join(f"• {ITEMS.get(r['item'],(r['item'],0))[0]} : {r['qty']}" for r in rows) if rows else "Vide"))

async def gather(interaction,action,key,lo,hi,xp):
    if not await authorized(interaction):return
    with connection() as db:
        player(db,interaction.user.id)
        wait=cooldown(db,interaction.user.id,action)
        if wait:
            msg=f"⏳ Patiente encore {wait} secondes."
        else:
            amount=random.randint(lo,hi)
            give(db,interaction.user.id,key,amount)
            msg=f"📦 +{amount} {ITEMS[key][0]} · "+award(db,interaction.user.id,xp)
    await respond(interaction,msg)

@bot.tree.command(name="mine",description="Miner du minerai")
async def mine(interaction:discord.Interaction):
    await gather(interaction,"mine","fer",1,4,12)

@bot.tree.command(name="couper",description="Couper du bois")
async def couper(interaction:discord.Interaction):
    await gather(interaction,"couper","bois",2,5,10)

@bot.tree.command(name="peche",description="Pêcher")
async def peche(interaction:discord.Interaction):
    await gather(interaction,"peche","poisson",1,4,11)

@bot.tree.command(name="travail",description="Travailler pour gagner de l'or")
async def travail(interaction:discord.Interaction):
    if not await authorized(interaction):return
    with connection() as db:
        player(db,interaction.user.id)
        wait=cooldown(db,interaction.user.id,"travail")
        msg=f"⏳ Encore {wait}s." if wait else "🔨 Travail terminé ! "+award(db,interaction.user.id,8,random.randint(20,50))
    await respond(interaction,msg)

async def combat_action(interaction,action,boss=False):
    if not await authorized(interaction):return
    with connection() as db:
        uid=interaction.user.id
        p=player(db,uid)
        if p["hp"]<=0:
            msg="💀 Tu es KO. Utilise /repos ou /utiliser potion."
        elif p["dungeon"]:
            msg="🚪 Termine ou quitte ton donjon avant un combat extérieur."
        else:
            wait=cooldown(db,uid,action)
            if wait:
                msg=f"⏳ Encore {wait}s avant ton prochain combat."
            else:
                tier=min(len(MONSTERS)-1,max(0,(p["level"]-1)//5))
                m=MONSTERS[random.randint(max(0,tier-1),tier)]
                win,hp,log,xp,gold=fight(p,m,boss)
                change(db,uid,hp=hp,wins=p["wins"]+int(win),losses=p["losses"]+int(not win))
                msg=f"{'🏆 Victoire' if win else '💀 Défaite'} contre **{m[0]}** !\n{log}\n❤️ {hp} PV"
                if win:
                    msg+="\n"+award(db,uid,xp,gold)
                    if random.random()<0.12:
                        give(db,uid,"cristal",1)
                        msg+="\n💎 Cristal trouvé !"
    await respond(interaction,msg)

@bot.tree.command(name="aventure",description="Explorer et combattre")
async def aventure(interaction:discord.Interaction):
    await combat_action(interaction,"aventure")

@bot.tree.command(name="chasse",description="Chasser un monstre")
async def chasse(interaction:discord.Interaction):
    await combat_action(interaction,"chasse")

@bot.tree.command(name="quete",description="Accomplir une quête de combat")
async def quete(interaction:discord.Interaction):
    await combat_action(interaction,"quete",True)

@bot.tree.command(name="quotidien",description="Récupérer une récompense chaque jour")
async def quotidien(interaction:discord.Interaction):
    if not await authorized(interaction):return
    today=time.strftime("%Y-%m-%d",time.gmtime())
    with connection() as db:
        p=player(db,interaction.user.id)
        if p["last_daily"]==today:
            msg="📅 Récompense quotidienne déjà récupérée (réinitialisation à 00h UTC)."
        else:
            change(db,interaction.user.id,last_daily=today)
            msg="🎁 Récompense du jour ! "+award(db,interaction.user.id,40,150)
            give(db,interaction.user.id,"potion",1)
    await respond(interaction,msg)

@bot.tree.command(name="boutique",description="Voir les prix des objets")
async def boutique(interaction:discord.Interaction):
    await respond(interaction,"🏪 **Boutique**\n"+"\n".join(f"`{k}` — {v[0]} : {v[1]} 🪙" for k,v in ITEMS.items())+"\n/acheter objet quantité")

@bot.tree.command(name="acheter",description="Acheter un objet")
@app_commands.describe(objet="Identifiant dans /boutique",quantite="Nombre à acheter")
async def acheter(interaction:discord.Interaction,objet:str,quantite:app_commands.Range[int,1,100]=1):
    if not await authorized(interaction):return
    with connection() as db:
        p=player(db,interaction.user.id)
        if objet not in ITEMS:msg="Objet inconnu. Consulte /boutique."
        elif p["gold"]<ITEMS[objet][1]*quantite:msg="🪙 Pas assez de pièces."
        else:
            give(db,interaction.user.id,objet,quantite)
            change(db,interaction.user.id,gold=p["gold"]-ITEMS[objet][1]*quantite)
            msg=f"✅ {quantite} × {ITEMS[objet][0]} acheté(s)."
    await respond(interaction,msg)

@bot.tree.command(name="vendre",description="Vendre des objets")
async def vendre(interaction:discord.Interaction,objet:str,quantite:app_commands.Range[int,1,100]=1):
    if not await authorized(interaction):return
    with connection() as db:
        p=player(db,interaction.user.id)
        if objet not in ITEMS:msg="Objet inconnu."
        elif item_qty(db,interaction.user.id,objet)<quantite:msg="Quantité insuffisante."
        else:
            give(db,interaction.user.id,objet,-quantite)
            gain=ITEMS[objet][1]*quantite//2
            change(db,interaction.user.id,gold=p["gold"]+gain)
            msg=f"💰 Vente réussie : +{gain} pièces."
    await respond(interaction,msg)

@bot.tree.command(name="fabriquer",description="Fabriquer un équipement ou une potion")
async def fabriquer(interaction:discord.Interaction,objet:str):
    if not await authorized(interaction):return
    with connection() as db:
        p=player(db,interaction.user.id)
        if objet not in RECIPES:msg="Recettes : "+", ".join(RECIPES)
        else:
            resources,price=RECIPES[objet]
            if p["gold"]<price or any(item_qty(db,interaction.user.id,k)<v for k,v in resources.items()):
                msg=f"Ressources insuffisantes. Recette : {resources} et {price} pièces."
            else:
                for k,v in resources.items():give(db,interaction.user.id,k,-v)
                give(db,interaction.user.id,objet,1)
                change(db,interaction.user.id,gold=p["gold"]-price)
                msg=f"🔨 {ITEMS[objet][0]} fabriqué !"
    await respond(interaction,msg)

@bot.tree.command(name="utiliser",description="Utiliser une potion de soin")
async def utiliser(interaction:discord.Interaction,objet:str="potion"):
    if not await authorized(interaction):return
    with connection() as db:
        p=player(db,interaction.user.id)
        if objet not in ("potion","grande_potion"):msg="Utilise potion ou grande_potion."
        elif item_qty(db,interaction.user.id,objet)<1:msg="Tu ne possèdes pas cet objet."
        elif p["hp"]>=p["max_hp"]:msg="Tes PV sont déjà au maximum."
        else:
            give(db,interaction.user.id,objet,-1)
            heal=40 if objet=="potion" else 100
            hp=min(p["max_hp"],p["hp"]+heal)
            change(db,interaction.user.id,hp=hp)
            msg=f"❤️ Soigné : {hp}/{p['max_hp']} PV."
    await respond(interaction,msg)

@bot.tree.command(name="equiper",description="Consommer un équipement pour améliorer ses statistiques")
async def equiper(interaction:discord.Interaction,objet:str):
    if not await authorized(interaction):return
    with connection() as db:
        p=player(db,interaction.user.id)
        if objet not in ("epee","armure"):msg="Équipements disponibles : epee, armure."
        elif item_qty(db,interaction.user.id,objet)<1:msg="Tu n'as pas cet équipement."
        else:
            give(db,interaction.user.id,objet,-1)
            if objet=="epee":change(db,interaction.user.id,atk=p["atk"]+3)
            else:change(db,interaction.user.id,defense=p["defense"]+2,max_hp=p["max_hp"]+10,hp=p["hp"]+10)
            msg="⚔️ Amélioration permanente appliquée !"
    await respond(interaction,msg)

@bot.tree.command(name="repos",description="Récupérer ses PV contre des pièces")
async def repos(interaction:discord.Interaction):
    if not await authorized(interaction):return
    with connection() as db:
        p=player(db,interaction.user.id)
        if p["hp"]==p["max_hp"]:msg="Tu es déjà en pleine forme."
        elif p["gold"]<15:msg="Il faut 15 pièces pour se reposer."
        else:
            change(db,interaction.user.id,hp=p["max_hp"],gold=p["gold"]-15)
            msg="🛏️ Repos terminé. PV restaurés !"
    await respond(interaction,msg)

@bot.tree.command(name="chevaux",description="Voir les chevaux disponibles")
async def chevaux(interaction:discord.Interaction):
    await respond(interaction,"🐴 **Écurie**\n"+"\n".join(f"`{k}` : {v[0]} pièces · +{v[1]} attaque" for k,v in HORSES.items())+"\n/acheter_cheval nom")

@bot.tree.command(name="acheter_cheval",description="Acheter et équiper un cheval")
async def acheter_cheval(interaction:discord.Interaction,nom:str):
    if not await authorized(interaction):return
    with connection() as db:
        p=player(db,interaction.user.id)
        if nom not in HORSES:msg="Cheval inconnu. Consulte /chevaux."
        elif p["gold"]<HORSES[nom][0]:msg="Pas assez de pièces."
        else:
            change(db,interaction.user.id,horse=nom,horse_level=1,gold=p["gold"]-HORSES[nom][0])
            msg=f"🐴 Ton nouveau cheval est **{nom}** !"
    await respond(interaction,msg)

@bot.tree.command(name="entrainer_cheval",description="Améliorer son cheval")
async def entrainer_cheval(interaction:discord.Interaction):
    if not await authorized(interaction):return
    with connection() as db:
        p=player(db,interaction.user.id)
        price=p["horse_level"]*100
        if not p["horse"]:msg="Achète d'abord un cheval."
        elif p["gold"]<price:msg=f"Entraînement : {price} pièces nécessaires."
        else:
            change(db,interaction.user.id,horse_level=p["horse_level"]+1,gold=p["gold"]-price)
            msg=f"🐴 Cheval niveau {p['horse_level']+1} !"
    await respond(interaction,msg)

@bot.tree.command(name="donjons",description="Voir les donjons solo")
async def donjons(interaction:discord.Interaction):
    await respond(interaction,"🏰 **Donjons**\n"+"\n".join(f"**{i+1}. {d[0]}** · niveau {d[1]}+ · {d[2]} salles" for i,d in enumerate(DUNGEONS))+"\n/entrer_donjon numero")

@bot.tree.command(name="entrer_donjon",description="Entrer dans un donjon en solo")
async def entrer_donjon(interaction:discord.Interaction,numero:app_commands.Range[int,1,16]):
    if not await authorized(interaction):return
    with connection() as db:
        p=player(db,interaction.user.id)
        name,level,floors=DUNGEONS[numero-1]
        if p["dungeon"]:msg="Tu es déjà dans un donjon."
        elif p["level"]<level:msg=f"Niveau {level} requis."
        elif p["hp"]<=0:msg="Soigne-toi avant d'entrer."
        else:
            change(db,interaction.user.id,dungeon=numero,dungeon_floor=0)
            msg=f"🚪 Entrée dans **{name}**. {floors} salles à traverser. Utilise /avancer_donjon."
    await respond(interaction,msg)

@bot.tree.command(name="avancer_donjon",description="Combattre dans la salle suivante")
async def avancer_donjon(interaction:discord.Interaction):
    if not await authorized(interaction):return
    with connection() as db:
        p=player(db,interaction.user.id)
        if not p["dungeon"]:msg="Entre d'abord dans un donjon avec /entrer_donjon."
        elif p["hp"]<=0:msg="Tu es KO. Utilise /quitter_donjon puis soigne-toi."
        else:
            index=p["dungeon"]-1
            name,level,floors=DUNGEONS[index]
            floor=p["dungeon_floor"]+1
            boss=floor==floors
            tier=min(len(MONSTERS)-1,index)
            m=MONSTERS[tier]
            win,hp,log,xp,gold=fight(p,m,boss)
            change(db,interaction.user.id,hp=hp,wins=p["wins"]+int(win),losses=p["losses"]+int(not win))
            if win:
                change(db,interaction.user.id,dungeon_floor=floor)
                msg=f"⚔️ **{name} — salle {floor}/{floors}**\n{log}\n❤️ {hp} PV\n"+award(db,interaction.user.id,xp,gold)
                if boss:
                    reward=200*(index+1)
                    msg+="\n👑 **DONJON TERMINÉ !**\n"+award(db,interaction.user.id,50*(index+1),reward)
                    give(db,interaction.user.id,"cristal",index+1)
                    change(db,interaction.user.id,dungeon=0,dungeon_floor=0)
            else:
                change(db,interaction.user.id,dungeon=0,dungeon_floor=0)
                msg=f"💀 Défaite salle {floor}. Donjon perdu.\n{log}"
    await respond(interaction,msg)

@bot.tree.command(name="quitter_donjon",description="Quitter le donjon en cours")
async def quitter_donjon(interaction:discord.Interaction):
    if not await authorized(interaction):return
    with connection() as db:
        player(db,interaction.user.id)
        change(db,interaction.user.id,dungeon=0,dungeon_floor=0)
    await respond(interaction,"🚪 Tu as quitté le donjon.")

@bot.tree.command(name="classement",description="Classement des personnages")
async def classement(interaction:discord.Interaction):
    with connection() as db:
        rows=db.execute("SELECT id,level,wins FROM players ORDER BY level DESC,wins DESC LIMIT 10").fetchall()
    await respond(interaction,"🏆 **Classement**\n"+("\n".join(f"{i+1}. <@{r['id']}> — niv. {r['level']} · {r['wins']} victoires" for i,r in enumerate(rows)) if rows else "Aucun joueur"))

@bot.tree.command(name="succes",description="Voir ses succès")
async def succes(interaction:discord.Interaction):
    if not await authorized(interaction):return
    with connection() as db:
        p=player(db,interaction.user.id)
        achievements=[
            ("Première victoire",p["wins"]>=1),
            ("Chasseur confirmé",p["wins"]>=25),
            ("Vétéran",p["level"]>=10),
            ("Maître aventurier",p["level"]>=30),
            ("Cavalier",bool(p["horse"])),
            ("Fortuné",p["gold"]>=5000),
        ]
        for name,done in achievements:
            if done:db.execute("INSERT OR IGNORE INTO achievements VALUES(?,?)",(interaction.user.id,name))
    await respond(interaction,"🏅 **Succès**\n"+"\n".join(("✅" if done else "⬜")+" "+name for name,done in achievements))

import progression as progression_extension
from progression import register as register_progression
register_progression(globals())
from expansion import register as register_expansion
register_expansion(globals())

from text_commands import register as register_text_commands
register_text_commands(bot)

@bot.event
async def on_ready():
    if not getattr(bot,"_synced",False):
        try:
            if GUILD_ID:
                guild=discord.Object(id=int(GUILD_ID))
                bot.tree.copy_global_to(guild=guild)
                await bot.tree.sync(guild=guild)
            else:
                await bot.tree.sync()
            bot._synced=True
        except discord.HTTPException as exc:
            print("Échec de synchronisation des commandes :",exc)
    print(f"Connecté : {bot.user}")

if __name__=="__main__":
    if not TOKEN:
        raise SystemExit("DISCORD_TOKEN manquant : configure le fichier .env.")
    init_db()
    bot.run(TOKEN)
