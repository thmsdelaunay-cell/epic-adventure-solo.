"""Extension niveau 100 : régions, monstres, métiers, équipement et donjons."""
import random
import time
from discord import app_commands

REGIONS = [
("Prairies d'Aube",1,["Rat des champs","Slime ambré","Corbeau noir","Sanglier farouche","Lutin","Renard","Loup gris","Chien sauvage"]),
("Bois de Brume",10,["Araignée venimeuse","Tréant","Bandit","Ours","Loup spectral","Dryade hostile","Frelon géant","Chasseur perdu"]),
("Désert de Verre",20,["Scorpion","Serpent de sable","Momie","Vautour","Dune vivante","Djinn mineur","Golem de verre","Hyène"]),
("Marais des Murmures",30,["Sangsue géante","Sorcière","Crapaud ancien","Spectre","Hydre juvénile","Moustique colossal","Zombie","Gardien vaseux"]),
("Pics de Givre",40,["Yéti","Loup blanc","Élémentaire de glace","Aigle des neiges","Golem gelé","Troll","Givrelin","Chevalier glacé"]),
("Cavernes de Braise",50,["Salamandre","Diablotin","Golem de lave","Chauve-souris ardente","Ver de feu","Démon cornu","Esprit de cendre","Lézard magmatique"]),
("Ruines Astrales",60,["Sentinelle","Automate","Mage errant","Spectre stellaire","Gardien runique","Éclat vivant","Archer spectral","Chevalier ancien"]),
("Cité Engloutie",70,["Sirène hostile","Crabe colossal","Naga","Requin d'ombre","Gardien corallien","Méduse","Esprit marin","Pirate maudit"]),
("Royaume du Néant",80,["Traqueur du vide","Abomination","Œil ancien","Démon supérieur","Ombre affamée","Chevalier du néant","Tisseur noir","Garde infernal"]),
("Trône Éternel",90,["Séraphin déchu","Titan d'obsidienne","Dragon ancien","Arbitre cosmique","Hydre royale","Colosse","Héraut final","Sentinelle éternelle"]),
]
MATERIALS={
"cuivre":("Cuivre",16),"argent":("Argent",45),"or_minerai":("Minerai d'or",85),
"mithril":("Mithril",160),"adamantite":("Adamantite",300),
"chene":("Chêne",20),"if":("Bois d'if",55),"ebene":("Ébène",110),
"bois_celeste":("Bois céleste",250),"algue":("Algue",10),
"truite":("Truite",18),"saumon":("Saumon",35),"anguille":("Anguille",65),
"poisson_lune":("Poisson-lune",130),"leviathan":("Écaille de léviathan",280),
"fragment_runique":("Fragment runique",170),"coeur_dragon":("Cœur de dragon",400),
"poussiere_astrale":("Poussière astrale",240),"tissu_ombre":("Tissu d'ombre",120),
}
JOBS={
"mineur":[("fer",1),("cuivre",1),("argent",12),("or_minerai",25),("mithril",45),("adamantite",75)],
"bucheron":[("bois",1),("chene",1),("if",18),("ebene",40),("bois_celeste",75)],
"pecheur":[("poisson",1),("truite",1),("saumon",12),("anguille",30),("poisson_lune",55),("leviathan",85)],
}
BOSS_NAMES=["Alpha sauvage","Ancien sylvestre","Souverain des dunes","Hydre des marais","Roi du blizzard","Seigneur de braise","Oracle astral","Impératrice des abysses","Monarque du néant","Empereur éternel"]
DUNGEON_NAMES=["Terrier ancestral","Sanctuaire des ronces","Pyramide scellée","Bastion noyé","Citadelle de givre","Forge volcanique","Observatoire perdu","Palais englouti","Faille du néant","Tour de l'éternité"]
GEAR_TIERS=[
("bronze",1,"cuivre","bois",3,2,10),
("argent",12,"argent","chene",7,4,20),
("or",25,"or_minerai","if",12,7,30),
("mithril",40,"mithril","ebene",19,11,45),
("adamantite",60,"adamantite","bois_celeste",28,17,65),
("astral",80,"poussiere_astrale","fragment_runique",40,25,90),
]
def register(env):
    bot=env["bot"]
    dbctx=env["connection"]
    player=env["player"]
    give=env["give"]
    qty=env["item_qty"]
    change=env["change"]
    award=env["award"]
    fight=env["fight"]
    respond=env["respond"]
    authorized=env["authorized"]
    items=env["ITEMS"]
    monsters=env["MONSTERS"]
    dungeons=env["DUNGEONS"]
    items.update(MATERIALS)
    for name,level,names in REGIONS:
        for i,m in enumerate(names):
            monsters.append((m,20+level*10+i*7,4+level//2+i,10+level*2+i*3,10+level*3+i*4))
    for i,(name,level,names) in enumerate(REGIONS):
        dungeons.append((DUNGEON_NAMES[i],level,3+i//2))
    # Expand the existing original system while preserving its first six dungeons.
    ext=env.get("progression_extension")
    if ext is not None:
        for i,name in enumerate(BOSS_NAMES):
            level=i*10+1
            ext.BOSSES.append((name,level,(name,130+level*19,10+level,60+level*5,90+level*8)))
        for i,(name,level,names) in enumerate(REGIONS):
            ext.BIOMES.append((name,level,[(m,25+level*11+j*7,5+level//2+j,15+level*2,18+level*3) for j,m in enumerate(names)],["cristal","essence"] if level>50 else ["fer","bois"]))
        for tier,required,metal,wood,atk,defense,hp in GEAR_TIERS:
            ext.GEAR["epee_"+tier]=({metal:7,wood:3},required*20,atk,0,0)
            ext.GEAR["armure_"+tier]=({metal:10,wood:2},required*25,0,defense,hp)
            items["epee_"+tier]=(f"Épée {tier}",required*70)
            items["armure_"+tier]=(f"Armure {tier}",required*85)
            env["RECIPES"]["epee_"+tier]=({metal:7,wood:3},required*20)
            env["RECIPES"]["armure_"+tier]=({metal:10,wood:2},required*25)

    def setup(db):
        db.execute("""CREATE TABLE IF NOT EXISTS professions(
            user_id INTEGER, job TEXT, level INTEGER DEFAULT 1,
            xp INTEGER DEFAULT 0, PRIMARY KEY(user_id,job))""")
        db.execute("""CREATE TABLE IF NOT EXISTS region_unlocks(
            user_id INTEGER PRIMARY KEY, best_region INTEGER DEFAULT 0)""")
        db.execute("""CREATE TABLE IF NOT EXISTS hunting_records(
            user_id INTEGER, monster TEXT, wins INTEGER DEFAULT 0,
            PRIMARY KEY(user_id,monster))""")
        db.execute("""CREATE TABLE IF NOT EXISTS job_cooldowns(
            user_id INTEGER, job TEXT, until_at INTEGER DEFAULT 0,
            PRIMARY KEY(user_id,job))""")

    def job_progress(db,uid,job):
        setup(db)
        db.execute("INSERT OR IGNORE INTO professions(user_id,job) VALUES(?,?)",(uid,job))
        return db.execute("SELECT level,xp FROM professions WHERE user_id=? AND job=?",(uid,job)).fetchone()

    @bot.tree.command(name="regions",description="Voir les dix régions et leurs monstres")
    async def regions(interaction):
        if not await authorized(interaction):return
        with dbctx() as db:p=player(db,interaction.user.id)
        await respond(interaction,"🗺️ **Régions — niveau 1 à 100**\n"+"\n".join(
            f"{'🔓' if p['level']>=level else '🔒'} **{name}** · niveau {level}+ · {len(mobs)} monstres"
            for name,level,mobs in REGIONS))

    @bot.tree.command(name="bestiary",description="Consulter les monstres d'une région")
    async def bestiary(interaction,region:app_commands.Range[int,1,10]):
        if not await authorized(interaction):return
        name,level,names=REGIONS[region-1]
        await respond(interaction,f"📖 **{name}** · niveau {level}+\n"+"\n".join(f"• {m}" for m in names))

    @bot.tree.command(name="metiers",description="Voir le niveau de tes métiers")
    async def metiers(interaction):
        if not await authorized(interaction):return
        with dbctx() as db:
            player(db,interaction.user.id)
            lines=[]
            for job in JOBS:
                p=job_progress(db,interaction.user.id,job)
                lines.append(f"**{job.title()}** : niveau {p['level']} · {p['xp']}/{p['level']*35} XP")
        await respond(interaction,"🛠️ **Métiers**\n"+"\n".join(lines)+"\nUtilise /exercer métier.")

    @bot.tree.command(name="exercer",description="Récolter des ressources et progresser dans un métier")
    @app_commands.choices(metier=[
        app_commands.Choice(name="Mineur",value="mineur"),
        app_commands.Choice(name="Bûcheron",value="bucheron"),
        app_commands.Choice(name="Pêcheur",value="pecheur")])
    async def exercer(interaction,metier:app_commands.Choice[str]):
        if not await authorized(interaction):return
        uid=interaction.user.id
        job=metier.value
        with dbctx() as db:
            p=player(db,uid)
            prof=job_progress(db,uid,job)
            now=int(time.time())
            timer=db.execute("SELECT until_at FROM job_cooldowns WHERE user_id=? AND job=?",(uid,job)).fetchone()
            if timer and timer["until_at"]>now:
                msg=f"⏳ Encore {timer['until_at']-now}s avant de recommencer."
            else:
                db.execute("""INSERT INTO job_cooldowns(user_id,job,until_at) VALUES(?,?,?)
                    ON CONFLICT(user_id,job) DO UPDATE SET until_at=excluded.until_at""",(uid,job,now+45))
                available=[(key,req) for key,req in JOBS[job] if prof["level"]>=req]
                weights=[max(1,35//(1+idx*idx)) for idx,_ in enumerate(available)]
                key=random.choices([x[0] for x in available],weights=weights,k=1)[0]
                amount=random.randint(1,4)
                give(db,uid,key,amount)
                xp=prof["xp"]+random.randint(8,16)
                level=prof["level"]
                while level<100 and xp>=level*35:
                    xp-=level*35
                    level+=1
                db.execute("UPDATE professions SET level=?,xp=? WHERE user_id=? AND job=?",(level,xp,uid,job))
                msg=f"🛠️ {job.title()} niveau {level} : {amount} × {items[key][0]}\n"+award(db,uid,5+level//3)
        await respond(interaction,msg)

    @bot.tree.command(name="equipements",description="Voir les paliers d'armes et armures")
    async def equipements(interaction):
        lines=[]
        for tier,required,metal,wood,atk,defense,hp in GEAR_TIERS:
            lines.append(f"**{tier.title()}** (niveau conseillé {required}) : épée +{atk} ATQ · armure +{defense} DEF, +{hp} PV")
        await respond(interaction,"⚔️ **Équipements évolutifs**\n"+"\n".join(lines)+"\nFabrique avec /fabriquer puis équipe avec /porter.")

    @bot.tree.command(name="chasser_region",description="Chasser un monstre dans une région débloquée")
    async def chasser_region(interaction,region:app_commands.Range[int,1,10]):
        if not await authorized(interaction):return
        uid=interaction.user.id
        with dbctx() as db:
            p=player(db,uid)
            name,required,mobs=REGIONS[region-1]
            if p["level"]<required:msg=f"🔒 Niveau {required} requis."
            elif p["dungeon"]:msg="Quitte ton donjon avant de chasser."
            elif p["hp"]<=0:msg="Tu es KO. Utilise /repos."
            else:
                setup(db)
                now=int(time.time())
                t=db.execute("SELECT until_at FROM job_cooldowns WHERE user_id=? AND job='region_hunt'",(uid,)).fetchone()
                if t and t["until_at"]>now:msg=f"⏳ Encore {t['until_at']-now}s."
                else:
                    db.execute("""INSERT INTO job_cooldowns(user_id,job,until_at) VALUES(?,'region_hunt',?)
                        ON CONFLICT(user_id,job) DO UPDATE SET until_at=excluded.until_at""",(uid,now+40))
                    monster_name=random.choice(mobs)
                    i=mobs.index(monster_name)
                    monster=(monster_name,20+required*10+i*7,4+required//2+i,10+required*2+i*3,10+required*3+i*4)
                    win,hp,log,xp,gold=fight(p,monster)
                    change(db,uid,hp=hp,wins=p["wins"]+int(win),losses=p["losses"]+int(not win))
                    msg=f"⚔️ **{name} — {monster_name}**\n{log}\n❤️ {hp} PV"
                    if win:
                        db.execute("""INSERT INTO hunting_records(user_id,monster,wins) VALUES(?,?,1)
                            ON CONFLICT(user_id,monster) DO UPDATE SET wins=wins+1""",(uid,monster_name))
                        msg+="\n🏆 "+award(db,uid,xp,gold)
                        possible=[k for k in MATERIALS if k not in ("coeur_dragon","leviathan")]
                        if random.random()<0.42:
                            rare=random.choice(possible[:min(len(possible),4+region*2)])
                            give(db,uid,rare,1)
                            msg+=f"\n🎁 Butin : {items[rare][0]}"
                    else:msg+="\n💀 Défaite."
        await respond(interaction,msg)

    @bot.tree.command(name="statistiques_chasse",description="Consulter les monstres déjà vaincus")
    async def statistiques_chasse(interaction):
        if not await authorized(interaction):return
        with dbctx() as db:
            player(db,interaction.user.id)
            setup(db)
            rows=db.execute("SELECT monster,wins FROM hunting_records WHERE user_id=? ORDER BY wins DESC LIMIT 20",(interaction.user.id,)).fetchall()
        await respond(interaction,"📜 **Bestiaire vaincu**\n"+("\n".join(f"{r['monster']} : {r['wins']}" for r in rows) if rows else "Aucune chasse régionale enregistrée."))

    @bot.tree.command(name="niveau_max",description="Voir la progression vers le niveau 100")
    async def niveau_max(interaction):
        if not await authorized(interaction):return
        with dbctx() as db:p=player(db,interaction.user.id)
        await respond(interaction,f"🌟 Niveau **{p['level']}** · objectif **100**\n✨ XP actuelle : {p['xp']}/{p['level']*75}\n🗺️ Régions débloquées : {sum(p['level']>=r[1] for r in REGIONS)}/10")
