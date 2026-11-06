# EPIC Adventure Solo 🏰

Bot RPG Discord **solo** en français, inspiré des RPG textuels : progression, combats, métiers, économie, chevaux et donjons. Projet original, non affilié à EPIC RPG.

## Fonctionnalités

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
