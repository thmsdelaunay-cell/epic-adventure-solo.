# EPIC Adventure Solo 🏰

Bot RPG Discord **solo** en français, inspiré des RPG textuels : progression, combats, métiers, économie, chevaux et donjons. Projet original, non affilié à EPIC RPG.

## Fonctionnalités

- Interface web locale de jeu : paysage fantasy, statistiques, catégories,
  actions cliquables, formulaires d'objets et journal d'aventure.

## Jouer dans le navigateur sur Windows

L'interface utilise **la même base SQLite et les mêmes actions que Discord**.
Elle n'a pas besoin de connecter un deuxième bot à Discord. Tu peux garder le bot
Discord lancé en parallèle. Les gains, l'inventaire et les cooldowns sont partagés.

1. Arrête le bot avant la mise à jour et fais une copie privée de ta sauvegarde
   `adventure.db` (ou du fichier indiqué par DATABASE_PATH) et de `.env`.
2. Copie les fichiers du projet et le dossier `web` **dans ton dossier habituel,
   celui qui contient ta vraie sauvegarde**. Garde ton `.env` et ta base existants.
   N'extrais pas la mise à jour pour jouer dans un nouveau dossier vide.
3. Dans ce dossier, lance `py -m pip install -r requirements.txt`.
4. Double-clique sur **JOUER_SUR_WINDOWS.bat**, ou exécute `py start_web.py`.
5. Le navigateur ouvre **http://127.0.0.1:8765**. Si nécessaire, ouvre cette adresse
   manuellement. Choisis ton personnage existant en vérifiant son identifiant
   Discord, son niveau et son or, puis clique **Entrer dans le royaume**.
6. Choisis une catégorie à gauche et une action. Les actions à paramètres ouvrent
   un formulaire. Le résultat apparaît dans le journal et les statistiques se mettent à jour.

Garde la fenêtre du jeu ouverte ; Ctrl+C l'arrête. Le navigateur ne demande jamais
ton token Discord. L'interface reste limitée à ton PC ; elle n'est pas un hébergement
public. OWNER_ID, s'il est renseigné, limite les personnages accessibles.

**Protection des sauvegardes :** le lanceur cherche la base à côté des fichiers du
jeu (sauf chemin absolu DATABASE_PATH), affiche son chemin, et refuse de créer
une nouvelle base. Si ta progression n'apparaît pas, ferme le jeu et retrouve
le bon fichier avant toute action. Les commandes utilisent immédiatement la base
sélectionnée ; il ne s'agit pas d'une démonstration.

L'interface affiche toutes les commandes enregistrées, y compris les extensions.
Les actions s'exécutent directement dans le moteur du jeu et leurs résultats
apparaissent sur le site ; elles ne publient pas de messages dans un salon Discord.

Tests : `python -m unittest test_text_commands test_web_game test_web_http`.
Ils emploient uniquement des sauvegardes temporaires.

## Fonctionnalités du moteur

- Personnage avec niveau, XP, PV, attaque, défense et or
- Combats aléatoires, chasse, quêtes, monstres et boss
- Six donjons progressifs jouables seul, avec salles et récompenses
- Ressources : mine, bûcheronnage, pêche et travail
- Inventaire, boutique, vente, recettes, fabrication et équipement
- Quatre types de chevaux, bonus de combat et entraînement
- Récompense quotidienne, repos, potions, succès et classement
- Cooldowns et sauvegarde automatique en SQLite
- Restriction optionnelle à un utilisateur Discord via `OWNER_ID`

## Installation pas à pas

1. Installe **Python 3.11 ou plus récent**.
2. Télécharge ce dépôt avec **Code → Download ZIP**, puis extrais-le.
3. Dans le dossier du projet, ouvre un terminal et lance :
   ```bash
   python -m pip install -r requirements.txt
   ```
4. Dans [Discord Developer Portal](https://discord.com/developers/applications), crée une application, ouvre **Bot**, crée/réinitialise son token et copie-le. **Ne publie jamais ce token**.
5. Copie `.env.example` vers `.env` et remplace `COLLE_TON_TOKEN_ICI` par ton token.
6. Dans le portail Discord, ouvre **Installation** ou **OAuth2 → URL Generator** et autorise les scopes **bot** et **applications.commands**. Accorde au bot les permissions **View Channels** et **Send Messages**, puis invite-le sur ton serveur personnel.
7. Pour limiter le bot à toi seul, active le mode développeur Discord, copie ton identifiant utilisateur et mets-le dans `OWNER_ID` (à la place de `0`). Tu peux renseigner `GUILD_ID` avec l'identifiant de ton serveur pour faire apparaître les commandes plus rapidement.
8. Démarre :
   ```bash
   python start.py
   ```
9. Sur ton serveur Discord, utilise `/commencer`, puis `/aide`.

Sur Windows, si `python` n'est pas reconnu, essaie `py`. Sur macOS/Linux, essaie `python3`.

**Important :** le bot doit rester lancé sur un ordinateur ou un hébergement pour répondre. Le fichier `adventure.db` contient les sauvegardes ; conserve-en des copies privées. Les commandes globales peuvent prendre un certain temps à apparaître si `GUILD_ID` n'est pas défini.

## Commandes

Toutes les commandes slash, y compris celles des extensions, ont un équivalent
textuel : remplace le slash par `rpg ` (avec un espace).
Exemples : `rpg hunt`, `rpg profil`, `rpg inventaire`, `rpg boss`,
`rpg equiper armure`, `rpg acheter potion 2`, `rpg exercer mineur`,
`rpg recolter bois`, `rpg reclamer_quete Chasseur novice`.
Les arguments, restrictions OWNER_ID, sauvegardes et cooldowns sont communs.
`equiper` garde son amélioration permanente ; `porter` remplace un équipement avancé.
Les réponses textuelles sont visibles dans le salon ; les refus privés sont envoyés
en message privé quand Discord l'autorise.

### Activer les messages et mettre à jour sur Windows

1. Dans [Discord Developer Portal](https://discord.com/developers/applications),
   sélectionne ton application → **Bot** → **Privileged Gateway Intents** →
   active **Message Content Intent**, puis enregistre. Le code active aussi cet intent.
2. Arrête le bot avec **Ctrl+C** dans sa fenêtre.
3. Fais une copie privée de `.env` et `adventure.db` dans un autre dossier.
   Si DATABASE_PATH pointe ailleurs, sauvegarde cette base à la place.
4. Sur GitHub, utilise **Code → Download ZIP**, puis extrais dans un dossier temporaire.
   Copie uniquement `bot.py`, `text_commands.py`, `progression.py`, `expansion.py`,
   `start.py` et `requirements.txt` dans ton dossier habituel du bot.
   Ne remplace ni `.env` ni `adventure.db` ; ne recrée pas `.env` depuis l'exemple.
5. Ouvre PowerShell dans ce dossier habituel et exécute :

   ```powershell
   py -m pip install -r requirements.txt
   py start.py
   ```

   Si tu utilises un environnement virtuel, utilise son Python à la place de `py`.
6. Attends **Connecté**, puis teste `rpg profil`, `rpg hunt` et `/profil`.
   Le bot doit pouvoir voir le salon et y envoyer des messages.

Ne partage jamais le contenu de `.env` ou ton token.

Vérifications hors connexion : `python -m compileall -q .` et
`python -m unittest test_text_commands`. Elles ne lancent aucune connexion Discord.

| Catégorie | Commandes |
| --- | --- |
| Personnage | `/commencer`, `/profil`, `/inventaire`, |
| Combat | `/aventure`, `/chasse`, `/quete` |
| Récompenses | `/quotidien`, `/travail` |
| Récolte | `/mine`, `/couper`, `/peche` |
| Boutique | `/boutique`, `/acheter`, `/vendre`, `/fabriquer` |
| Objets | `/equiper`, `/utiliser`, `/repos` |
| Chevaux | `/chevaux`, `/acheter_cheval`, `/entrainer_cheval` |
| Donjons | `/donjons`, `/entrer_donjon`, `/avancer_donjon`, `/quitter_donjon` |
| Divers | `/succes`, `/classement`, `/aide` |

*Pour se soigner, utiliser `/utiliser potion` ou `/repos` (il n'existe pas de commande `/soigner`).

## Limites actuelles

Cette première version est une **base jouable** et non une reproduction exhaustive d'EPIC RPG. Les six donjons sont originaux ; le contenu, les mécaniques et l'équilibrage pourront être étendus. Le bot n'est pas encore déployé sur un hébergement permanent et n'a pas été testé sur un vrai serveur Discord.

## Extension progression (nouvelle version)

Le fichier `progression.py` ajoute `/hunt`, `/boss`, `/quetes`, `/reclamer_quete`, `/recolter`, `/crafts` et `/porter`.

- `/hunt` sélectionne un biome et des monstres selon le niveau ; les ressources ont des probabilités de butin distinctes.
- `/boss` propose quatre boss avec un délai de 5 minutes et des reliques.
- `/quetes` affiche six objectifs permanents ; `/reclamer_quete nom` récupère la récompense.
- `/recolter` permet pêche, bois et minerai avec une chance de butin rare ; `/crafts` affiche les recettes et `/fabriquer` les réalise.
- `/porter` équipe les nouvelles armes et armures en remplaçant l'ancien objet, sans cumul infini des bonus.

**Note :** les anciennes commandes `/mine`, `/couper`, `/peche` et `/chasse` restent utilisables, mais les objectifs de quête avancés sont comptabilisés avec `/recolter` et `/hunt`. Le bot doit être redémarré après une mise à jour. Cette extension n'a pas encore été validée par des tests d'intégration sur Discord.

## Extension progression niveau 100

- **10 régions** et **80 monstres régionaux** : `/regions`, `/bestiary`, `/chasser_region`, `/statistiques_chasse`
- **10 nouveaux donjons** : 16 donjons solo au total, avec accès par `/donjons` puis `/entrer_donjon numero`
- **10 boss supplémentaires** ajoutés au système `/boss`
- **3 métiers progressifs** (mineur, bûcheron, pêcheur), chacun jusqu'au niveau 100 : `/metiers` et `/exercer`
- **6 paliers d'équipement** (bronze, argent, or, mithril, adamantite, astral) : `/equipements`, `/fabriquer`, `/porter`
- **20 nouvelles ressources** pour les crafts et les loots
- **Progression du personnage plafonnée au niveau 100** : `/niveau_max`

Les anciennes commandes sont conservées. Les nouveaux donjons sont des combats solo par salles, pas une reproduction exacte des donjons d'EPIC RPG. La logique de progression et les probabilités de butin sont une première version à équilibrer lors des tests.

Une vérification automatique Python est configurée dans GitHub Actions ; elle ne remplace pas des tests réels sur un serveur Discord.
