"""Contenu avancé : chasse, butin, artisanat, quêtes et boss solo."""
import random
import time
from discord import app_commands

# Toutes les récompenses sont originales.
BIOMES = [
    ("Prairie",1,[("Rat géant",20,4,9,9),("Sanglier",32,6,12,13)],["peau","herbe"]),
    ("Bois obscur",5,[("Araignée",55,9,19,23),("Bandit",70,11,24,29)],["peau","bois_dur"]),
    ("Marais",10,[("Spectre",110,16,35,44),("Troll",145,19,43,55)],["essence","herbe"]),
    ("Montagnes",18,[("Wyverne",215,28,65,86),("Géant",255,30,72,98)],["minerai_rare","ecaille"]),
    ("Abîme",28,[("Démon",370,40,105,140),("Gardien",450,47,120,160)],["essence","cristal"]),
]
DROPS = {"peau":("Peau",14),"herbe":("Herbe médicinale",9),
         "bois_dur":("Bois dur",32),"essence":("Essence magique",65),
         "minerai_rare":("Minerai rare",70),"ecaille":("Écaille",90),
         "perle":("Perle",110),"poisson_rare":("Poisson rare",75),
         "bois_ancien":("Bois ancien",85),"relique":("Relique de boss",250)}
GEAR = {
    "lame_fer":({"fer":8,"bois":3},75,5,0,0),
    "lame_spectrale":({"minerai_rare":5,"essence":4,"cristal":2},650,14,0,0),
    "armure_cuir":({"peau":8,"bois":2},90,0,4,15),
    "armure_ecaille":({"ecaille":6,"minerai_rare":4},850,0,12,40),
    "elixir":({"herbe":5,"poisson_rare":2},100,0,0,0),
}
BOSSES = [
    ("Roi des sangliers",3,("Roi des sangliers",170,13,75,110)),
    ("Reine araignée",10,("Reine araignée",340,24,145,220)),
    ("Titan de pierre",20,("Titan de pierre",650,38,290,450)),
    ("Seigneur des abîmes",30,("Seigneur des abîmes",1050,57,480,750)),
]
QUESTS = [
    ("Chasseur novice", "hunt", 3, 75, 120),
    ("Chasseur aguerri", "hunt", 12, 220, 360),
    ("Mineur", "mine", 8, 95, 150),
    ("Bûcheron", "couper", 8, 95, 150),
    ("Pêcheur", "peche", 8, 95, 150),
    ("Vainqueur de boss", "boss", 2, 300, 450),
]

def register(env):
    bot=env["bot"]
    dbctx=env["connection"]
    player=env["player"]
    give=env["give"]
    item_qty=env["item_qty"]
    change=env["change"]
    award=env["award"]
    fight=env["fight"]
    respond=env["respond"]
    authorized=env["authorized"]
    cooldown=env["cooldown"]
    items=env["ITEMS"]
    recipes=env["RECIPES"]
    items.update(DROPS)
    items.update({k:(k.replace("_"," ").title(),max(100,cost*2)) for k,(_,cost,*_) in GEAR.items()})
    recipes.update({k:(materials,cost) for k,(materials,cost,*_) in GEAR.items()})

    # Initialiser les tables à la première invocation (compatible avec les sauvegardes existantes).
    def prepare(db):
        db.execute("""CREATE TABLE IF NOT EXISTS counters(
            user_id INTEGER, action TEXT, value INTEGER DEFAULT 0,
            PRIMARY KEY(user_id,action))""")
        db.execute("""CREATE TABLE IF NOT EXISTS quest_claims(
            user_id INTEGER, quest TEXT, PRIMARY KEY(user_id,quest))""")
        db.execute("""CREATE TABLE IF NOT EXISTS equipment(
            user_id INTEGER PRIMARY KEY, weapon TEXT DEFAULT '',
            armor TEXT DEFAULT '')""")
        db.execute("""CREATE TABLE IF NOT EXISTS boss_timers(
            user_id INTEGER PRIMARY KEY, ready_at INTEGER DEFAULT 0)""")

    def count(db,uid,action,amount=1):
        prepare(db)
        db.execute("""INSERT INTO counters(user_id,action,value) VALUES(?,?,?)
            ON CONFLICT(user_id,action) DO UPDATE SET value=value+excluded.value""",
            (uid,action,amount))

    def progress(db,uid,action):
        prepare(db)
        r=db.execute("SELECT value FROM counters WHERE user_id=? AND action=?",(uid,action)).fetchone()
        return r["value"] if r else 0

    def loot(db,uid,options,rare_chance=0.18):
        if random.random()>0.72:
            return ""
        key=random.choice(options)
        if key in ("minerai_rare","ecaille","essence","bois_ancien","perle","poisson_rare") and random.random()>rare_chance:
            return ""
        qty=random.randint(1,2)
        give(db,uid,key,qty)
        return f"\n🎁 Butin : {qty} × {items[key][0]}"

    @bot.tree.command(name="hunt",description="Chasser des monstres avec butin variable selon la zone")
    async def hunt(interaction):
        if not await authorized(interaction):return
        uid=interaction.user.id
        with dbctx() as db:
            p=player(db,uid)
            if p["dungeon"]:
                msg="Quitte ton donjon avant de chasser."
            elif p["hp"]<=0:
                msg="Tu es KO : utilise /repos."
            else:
                wait=cooldown(db,uid,"chasse")
                if wait:msg=f"⏳ Attends {wait} secondes."
                else:
                    available=[b for b in BIOMES if p["level"]>=b[1]]
                    zone=available[-1]
                    monster=random.choice(zone[2])
                    win,hp,log,xp,gold=fight(p,monster)
                    change(db,uid,hp=hp,wins=p["wins"]+int(win),losses=p["losses"]+int(not win))
                    msg=f"🌲 **{zone[0]}** — {monster[0]}\n{log}\n❤️ {hp} PV"
                    if win:
                        count(db,uid,"hunt")
                        msg+="\n🏆 Victoire ! "+award(db,uid,xp,gold)
                        msg+=loot(db,uid,zone[3])
                    else:msg+="\n💀 Défaite."
        await respond(interaction,msg)

    @bot.tree.command(name="boss",description="Affronter un boss solo avec butin spécial")
    async def boss(interaction):
        if not await authorized(interaction):return
        uid=interaction.user.id
        with dbctx() as db:
            prepare(db)
            p=player(db,uid)
            available=[b for b in BOSSES if p["level"]>=b[1]]
            timer=db.execute("SELECT ready_at FROM boss_timers WHERE user_id=?",(uid,)).fetchone()
            now=int(time.time())
            if p["dungeon"]:msg="Quitte ton donjon avant de défier un boss."
            elif p["hp"]<=0:msg="Tu es KO : utilise /repos."
            elif not available:msg="Niveau 3 requis pour affronter ton premier boss."
            elif timer and timer["ready_at"]>now:msg=f"⏳ Prochain boss dans {timer['ready_at']-now} secondes."
            else:
                name,level,monster=available[-1]
                db.execute("""INSERT INTO boss_timers VALUES(?,?)
                  ON CONFLICT(user_id) DO UPDATE SET ready_at=excluded.ready_at""",(uid,now+300))
                win,hp,log,xp,gold=fight(p,monster)
                change(db,uid,hp=hp,wins=p["wins"]+int(win),losses=p["losses"]+int(not win))
                msg=f"👹 **{name}**\n{log}\n❤️ {hp} PV"
                if win:
                    count(db,uid,"boss")
                    give(db,uid,"relique",1)
                    msg+="\n🏆 Boss vaincu ! "+award(db,uid,xp,gold)+"\n🎁 1 × Relique de boss"
                    msg+=loot(db,uid,["essence","ecaille","minerai_rare"],0.8)
                else:msg+="\n💀 Défaite. Reviens plus fort !"
        await respond(interaction,msg)

    @bot.tree.command(name="quetes",description="Afficher les objectifs et récompenses des quêtes")
    async def quetes(interaction):
        if not await authorized(interaction):return
        with dbctx() as db:
            uid=interaction.user.id
            player(db,uid)
            prepare(db)
            lines=[]
            for name,action,target,xp,gold in QUESTS:
                current=progress(db,uid,action)
                claimed=db.execute("SELECT 1 FROM quest_claims WHERE user_id=? AND quest=?",(uid,name)).fetchone()
                lines.append(f"{'✅' if claimed else '🟢' if current>=target else '⬜'} **{name}** {min(current,target)}/{target} · {xp} XP, {gold} 🪙")
        await respond(interaction,"📜 **Quêtes permanentes**\n"+"\n".join(lines)+"\nUtilise /reclamer_quete nom.")

    @bot.tree.command(name="reclamer_quete",description="Récupérer la récompense d'une quête terminée")
    async def reclamer_quete(interaction,nom:str):
        if not await authorized(interaction):return
        with dbctx() as db:
            uid=interaction.user.id
            player(db,uid)
            prepare(db)
            match=next((q for q in QUESTS if q[0].lower()==nom.lower()),None)
            if not match:msg="Quête inconnue. Consulte /quetes."
            else:
                name,action,target,xp,gold=match
                claimed=db.execute("SELECT 1 FROM quest_claims WHERE user_id=? AND quest=?",(uid,name)).fetchone()
                if claimed:msg="Récompense déjà récupérée."
                elif progress(db,uid,action)<target:msg=f"Objectif non atteint : {progress(db,uid,action)}/{target}."
                else:
                    db.execute("INSERT INTO quest_claims VALUES(?,?)",(uid,name))
                    msg="📜 Quête terminée ! "+award(db,uid,xp,gold)
        await respond(interaction,msg)

    @bot.tree.command(name="recolter",description="Récolter du bois ou pêcher avec chance de ressource rare")
    @app_commands.choices(metier=[
        app_commands.Choice(name="Bûcheronnage",value="bois"),
        app_commands.Choice(name="Pêche",value="poisson"),
        app_commands.Choice(name="Minage",value="fer")])
    async def recolter(interaction,metier:app_commands.Choice[str]):
        if not await authorized(interaction):return
        uid=interaction.user.id
        key=metier.value
        action={"bois":"couper","poisson":"peche","fer":"mine"}[key]
        with dbctx() as db:
            p=player(db,uid)
            wait=cooldown(db,uid,action)
            if wait:msg=f"⏳ Encore {wait} secondes."
            else:
                qty=random.randint(1,5)
                give(db,uid,key,qty)
                count(db,uid,action,qty)
                msg=f"🧰 {qty} × {items[key][0]} · "+award(db,uid,10+p["level"]//3)
                special={"bois":"bois_ancien","poisson":"poisson_rare","fer":"minerai_rare"}[key]
                if random.random()<min(0.35,0.08+p["level"]*0.004):
                    give(db,uid,special,1)
                    msg+=f"\n✨ Trouvaille rare : {items[special][0]} !"
                if key=="poisson" and random.random()<0.05:
                    give(db,uid,"perle",1)
                    msg+="\n🦪 Perle trouvée !"
        await respond(interaction,msg)

    @bot.tree.command(name="crafts",description="Voir les recettes avancées d'armes, armures et potions")
    async def crafts(interaction):
        lines=[]
        for name,(materials,cost,*_) in GEAR.items():
            ingredients=", ".join(f"{v} × {items[k][0]}" for k,v in materials.items())
            lines.append(f"**{name}** : {ingredients} + {cost} 🪙")
        await respond(interaction,"🔨 **Recettes avancées**\n"+"\n".join(lines)+"\nUtilise /fabriquer objet.")

    @bot.tree.command(name="porter",description="Équiper une arme ou armure craftée, sans empiler les bonus")
    async def porter(interaction,objet:str):
        if not await authorized(interaction):return
        uid=interaction.user.id
        with dbctx() as db:
            prepare(db)
            p=player(db,uid)
            if objet not in GEAR or objet=="elixir":
                msg="Équipements : "+", ".join(k for k in GEAR if k!="elixir")
            elif item_qty(db,uid,objet)<1:
                msg="Tu ne possèdes pas cet objet. Fabrique-le d'abord."
            else:
                materials,cost,atk,defense,health=GEAR[objet]
                slot="weapon" if atk else "armor"
                old=db.execute("SELECT weapon,armor FROM equipment WHERE user_id=?",(uid,)).fetchone()
                previous=old[slot] if old else ""
                if previous==objet:
                    msg="Cet équipement est déjà porté."
                else:
                    old_atk=old_def=old_hp=0
                    if previous in GEAR:
                        _,_,old_atk,old_def,old_hp=GEAR[previous]
                    give(db,uid,objet,-1)
                    if previous:give(db,uid,previous,1)
                    db.execute("INSERT OR IGNORE INTO equipment(user_id) VALUES(?)",(uid,))
                    db.execute(f"UPDATE equipment SET {slot}=? WHERE user_id=?",(objet,uid))
                    new_max=p["max_hp"]-old_hp+health
                    change(db,uid,atk=p["atk"]-old_atk+atk,
                           defense=p["defense"]-old_def+defense,
                           max_hp=new_max,hp=min(new_max,p["hp"]+max(0,health-old_hp)))
                    msg=f"🛡️ {objet} équipé ! Ancien équipement remis dans l'inventaire."
        await respond(interaction,msg)
