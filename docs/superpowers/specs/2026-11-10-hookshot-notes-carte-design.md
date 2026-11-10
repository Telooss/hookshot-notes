# Hookshot Notes — carte interactive en direct (v1)

*Document de conception — 10 novembre 2026*

## Intention

Le remake d'Ocarina of Time sur Switch 2 a une appli compagnon, « Zelda Notes », dont la fonction phare est une carte
interactive : position du joueur en temps réel, pourcentage de complétion, et objets importants de la zone
(Skulltulas d'or, coffres, quarts de cœur…). Les joueurs qui font tourner le jeu sur PC avec **Hookshot** (portage
recompilé du jeu, construit par chacun à partir de sa propre cartouche) n'ont pas accès à cette appli.

Hookshot Notes recrée cette carte : on lance l'outil, une page s'ouvre, et on la consulte sur son téléphone ou sur un
second écran pendant qu'on joue. Le but : savoir sans chercher ce qu'il y a autour de soi et où aller pour le récupérer,
comme avec les cartes interactives qui existent pour Breath of the Wild et Tears of the Kingdom.

Le projet sera publié sur un dépôt GitHub public (`Telooss/hookshot-notes`) pour les autres joueurs de Hookshot.

## Objectifs (v1)

- Une page web, ouverte dans un navigateur sur le PC, sur un téléphone ou sur un second écran du même réseau local.
- **Carte plein écran** dans le style du jeu (disposition « A » validée sur maquette) :
  - la vraie carte de la zone où se trouve Link, zoomable et déplaçable au doigt ;
  - la flèche de Link qui bouge en direct ;
  - le nom du lieu dans le ruban du jeu, en haut ;
  - les compteurs de la zone (Skulltulas, coffres, quarts de cœur), en haut à droite ;
  - des filtres par type d'objet (Skulltulas, coffres, quarts de cœur, lieux comme boutiques et fées, sorties), en bas ;
  - un bouton pour recentrer la carte sur Link.
- **La carte suit Link** : en changeant de zone, la page bascule toute seule sur la bonne carte, en version enfant ou adulte
  selon la carte chargée par le jeu. Si le joueur fait glisser la carte, elle arrête de suivre Link jusqu'au bouton recentrer.
- **Donjons** : un sélecteur d'étage (le jeu a une carte par étage).
- **Deux modes**, au choix sur la page :
  - **Spoiler** : en entrant dans une zone, tous les objets à trouver sont affichés ; ceux déjà pris portent l'icône
    « cochée » du jeu. Pour viser le 100 %.
  - **Tracker** : seuls les objets déjà ramassés sont affichés. Pour garder la découverte.
  - Dans les deux modes, la position de Link est affichée.
- **Pourcentage de complétion** affiché sur la page.
- **Seules les zones déjà visitées** sont accessibles sur la carte (comme Zelda Notes).
- **Style Zelda** : cartes, icônes, décors (ruban de nom de lieu, filets décoratifs) et polices sont ceux du jeu.
- **Le plus simple à ajouter à Hookshot** : un seul exécutable à poser dans le dossier Hookshot.

## Hors périmètre (v1)

Les autres fonctions de Zelda Notes viendront peut-être plus tard, pas maintenant : journal du jour, quêtes des rumeurs,
ocarina virtuelle, partitions, quiz, studio photo, statistiques de jeu (« herbe coupée, pots cassés »).

## Ce qu'il ne faut surtout pas faire

- **Publier quoi que ce soit qui appartient à Nintendo** dans le dépôt : ni cartes, ni icônes, ni polices, ni textes, ni
  données extraites du jeu (liste des objets, positions…). Tout est extrait de la copie du joueur, sur sa machine.
- **Écrire dans la mémoire du jeu ou dans ses sauvegardes**. L'outil ne fait que lire.
- **Modifier Hookshot** ou ses fichiers.
- **Gêner le jeu** : pas de ralentissement perceptible, pas de plantage du jeu si l'outil plante.
- **Exposer la page sur Internet** : réseau local uniquement.

## Contraintes

- **Windows**, à côté d'un dossier Hookshot construit (testé avec Hookshot `v2.0.10`, jeu en mise à jour `2.0.0`,
  build ID du code `e0f3ccfaf50065ae4ea01eb5aeb13b1a45da3348`).
- **Version du jeu** : l'outil ne fonctionnera qu'avec la version analysée. Il doit vérifier la version au démarrage
  et le dire clairement s'il ne la reconnaît pas, plutôt que d'afficher des données fausses.
- **Rien à installer pour le joueur** : un seul fichier, sans Python à installer.
- **Lecture mémoire en lecture seule** : le processus du jeu est ouvert avec les seuls droits de lecture
  (`PROCESS_VM_READ | PROCESS_QUERY_INFORMATION`).

## Ce qui a été décidé avec le porteur du projet

- Disposition **A** (carte plein écran) — validée sur maquette.
- **Style Zelda** avec les ressources du jeu.
- **Modes Spoiler et Tracker**.
- **Dépôt public sans ressources du jeu** ; extraction depuis la copie du joueur.
- **Une page web** consultable sur téléphone ou second écran.
- **Le plus simple à ajouter à Hookshot**.
- **Un raccourci « Hookshot Notes »** qui démarre le jeu et la carte ensemble.
- Nom du projet : **Hookshot Notes**.
- Périmètre v1 = la carte uniquement.

## Mes choix (à valider en relisant)

- **Lancement** : `hookshot-notes.exe` posé dans le dossier Hookshot. Un double-clic :
  1. au premier lancement, extrait les ressources depuis `romfs/` (quelques minutes, une seule fois) vers un dossier
     local (`hookshot-notes-data/` à côté de l'exe), et crée le raccourci **« Hookshot Notes »** sur le Bureau
     (décidé avec le porteur du projet) ; c'est ce raccourci qu'on utilise ensuite pour jouer ;
  2. démarre le serveur et ouvre la page sur le PC, avec un **QR code** donnant l'adresse réseau local à scanner
     depuis le téléphone ;
  3. lance le jeu via le lanceur `hookshot.exe` de Hookshot s'il ne tourne pas déjà, sinon s'y branche ;
  4. retrouve les données en mémoire et met à jour toutes les pages ouvertes en direct.
- **Technique** : Python (les décodeurs écrits pendant l'étude sont en Python), emballé en un seul `.exe` (PyInstaller) ;
  page web légère avec une bibliothèque de carte zoomable de type Leaflet ; mises à jour poussées aux pages ouvertes.
- **Animation** : la position est lue environ 2 fois par seconde par le jeu ; la page anime la flèche entre deux
  lectures pour rester fluide.
- **Compteurs en mode Tracker** : uniquement le nombre trouvé (« 1 Skulltula »), sans le total, qui serait déjà un indice.
- **Pourcentage de complétion** : objets ramassés / total des objets recensés (coffres, Skulltulas d'or, quarts de cœur).
- **Langue** : noms de lieux tirés des textes du jeu dans la langue choisie dans Hookshot (`language.txt`) ; interface
  de la page en français pour commencer.
- **Sécurité réseau** : serveur sur le réseau local seulement, en lecture seule (la page ne peut rien envoyer au jeu).

## Ce que l'étude a établi (faits vérifiés)

### Fichiers du jeu

- Moteur de Tears of the Kingdom : fichiers `.zs` compressés en zstd avec les dictionnaires de `Pack/ZsDic.pack.zs`
  (un SARC contenant `zs.zsdic`, `pack.zsdic`, `bcett.byml.zsdic`, `bkprb.zsdic`). Certains fichiers n'utilisent pas de
  dictionnaire : le décompresseur doit lire l'ID de dictionnaire de la trame zstd.
- BYML v7, en petit-boutiste (`YB`) **ou en gros-boutiste** (`BY`, par ex. `GameDataList`) : le lecteur doit gérer les deux.
- Textures BNTX de plateforme « Ounc » (Switch 2). Rangement des pixels : celui de la Tegra X1 (GOB 64×8) **avec les
  bits 5 et 6 de l'adresse dans le GOB échangés**.
- Polices `.bfotf`/`.bfttf` : en-tête de 8 octets puis OpenType chiffré par un XOR de période 4, clé `a6 01 85 02`.

### Cartes

- Images : `UI/CustomTex/Map/Field/<Zone>_<Child|Adult>_00.bntx.zs` (102 fichiers) et
  `UI/CustomTex/Map/Dungeon/<Donjon>_<Étage>_{Main,Back,Grad,Alpha,…}.bntx.zs` (179 calques). 2000×1440 px, ASTC 5×5
  (extérieurs) ou 6×6 (donjons), sRGB.
- `Game/MapMenuInfo/…bgyml` : 31 lieux (20 extérieurs puis 10 donjons puis le château de Ganon), avec pour chacun ses
  noms de carte (`BancName`, enfant/adulte) et ses textures.
- `Game/MapCaptureInfo/…bgyml` : 36 caméras vues de dessus (`CameraPos` X/Z, `Height`). Les 30 premières suivent l'ordre
  de `MapMenuInfo`.
- **Conversion monde → image** (vérifiée sur la forêt Kokiri et la plaine d'Hyrule) :
  `px = 1000 + (x − CameraPos.X) × 1440 / Height`, `py = 720 + (z − CameraPos.Z) × 1440 / Height`.

### Objets

- `Banc/BancBasedResource/MapParam.byml.zs` : 54 cartes. Pour les extérieurs, des listes au premier niveau ; pour les
  donjons, une liste `Floor` (avec `TransY` par étage). Types : `TBox` (coffres), `CollectSign`/`CollectSignAll`
  (Skulltulas d'or), `CollectHeart`/`CollectHeartAll` (quarts de cœur), `Facility` (boutiques, fées…, avec `IconType`),
  `EntranceAnchor` (sorties, avec `Location` de destination), `Door`, `StoneTablet`. Chacun a un `InstanceID` (u64) et
  une position `Trans`.
- Icônes du jeu dans `UI/Layout2Archive/Common…bntx.zs` : `MapIconTreasure_00/_01`, `MapIconCollectSkullSign_00` et
  `…Check_00`, `MapIconCollectHeartPiece_00` et `…Check_00`, `MapIconPlayer_00..02`, `MapIconDoor_01`, icônes de
  boutiques et lieux ; décors `MapLocationNameBgFill_00`, `MapLocationNameBgOutline_00`, `LocationDecoLine_00`.
- Polices : `CetraDisplayPro-Medium` (titres), `ClarimoUDPE-*` (texte).

### Données de partie (GameData)

- `GameData/GameDataList.Product.110.byml.zs` : noms des drapeaux hachés en **MurmurHash3 32 bits** (confirmé :
  `PlayerStatus.Life`, `PlayerStatus.MaxLife`, `PlayerStatus.CurrentRupee`, `PlayerStatus.SavePos` existent).
- Les `InstanceID` des 126 coffres de donjon et de toutes les Skulltulas (`CollectSign*`) sont **exactement** des clés
  de drapeaux `Bool64bitKey` : l'état « ramassé » de ces objets est donc un drapeau de partie.
- Sauvegardes : `user/save/<compte>/slot_NN/progress.sav`, même format que TotK (en-tête `04 03 02 01`, paires
  hash/valeur ; les valeurs larges sont des décalages dans le fichier). Lecture vérifiée (vie, rubis, position de sauvegarde).

### Mémoire du jeu en direct

- La mémoire Switch est recopiée dans le processus Windows à l'adresse **`0x100000000000 + adresse Switch`**. Code du
  jeu à `0x80000000`, tas à `0x1000000000` (environ 6,9 Go).
- Hookshot n'expose aucune interface (ni réseau, ni pipe) : il faut lire sa mémoire.
- **Enregistrement « carte actuelle + position »** trouvé dans le stockage GameData en direct :
  `[u64 pointeur vers le texte][u32 capacité = 0x40][texte : nom de carte, 64 octets][8 octets à zéro][3 float : x, y, z]`.
  Le pointeur pointe sur le texte lui-même. Le nom de carte est un `BancName` (ex. `KokiriForest_Child`, `HyruleField_Child`).
  - Mis à jour environ 2 fois par seconde pendant un déplacement (80 mises à jour sur 45 s de course ; trajet mesuré
    171 unités contre 174 pour la physique).
  - **Même adresse avant et après un changement de zone** ; le nom de carte suit.
  - Retrouvé par recherche de ce motif dans toute la mémoire en environ 10 s : en ne gardant que les noms connus de
    `MapParam` et une position plausible, il reste un seul enregistrement vivant (plus un enregistrement vide à zéro).
- Des copies de la position côté physique existent (mises à jour à chaque image) mais dans une mémoire temporaire,
  sans moyen fiable de les retrouver pour l'instant.

## Ce qui reste à trouver pendant la construction

1. **État « ramassé » en direct** : trouver où vivent les drapeaux `Bool64bitKey` en mémoire. À défaut, lire la
   sauvegarde (mise à jour seulement aux sauvegardes).
2. **Quarts de cœur** : leurs `InstanceID` ne sont pas des `Bool64bitKey` ; piste : les champs `HeartPieceHash0/1` des
   `Facility` et les drapeaux nommés (`OpenedHeartPiece`, `AppearHeartPiece` existent dans les chaînes de `GameDataList`).
3. **Zones visitées** : trouver le drapeau correspondant (pistes : `UnopenMap`, `FieldMap`, `DungeonMap`, `WorldMap`).
4. **Orientation de Link** pour tourner la flèche (non trouvée ; à défaut, la déduire du déplacement).
5. **Intérieurs** (maisons, boutiques) : leurs noms de carte ne sont pas dans `MapParam` ; décider quoi afficher
   (probablement la zone extérieure parente, flèche à l'entrée).
6. **Étage courant en donjon** : à déduire de la hauteur de Link comparée aux `TransY` des étages.
7. **Caméras de capture 30 à 35** (au-delà des 30 lieux du menu) : à associer à leurs cartes (château, gymnase gerudo…).
8. **Description des objets** (« près de la boutique ») : pas trouvée dans les données ; la v1 peut s'en passer.

## Ce qui bloque la sortie de la v1, et les solutions de repli (mes choix)

- **Bloquant** : la carte de la zone, la position de Link en direct, le changement de zone automatique, le mode Spoiler,
  les icônes et le style du jeu, le lancement par le raccourci.
- **État « ramassé »** : si les drapeaux ne sont pas trouvés en mémoire, on lit la sauvegarde. Les coches et le mode
  Tracker ne se mettent alors à jour qu'aux sauvegardes du joueur — **accepté par le porteur du projet pour la v1** ;
  la lecture en direct reste un objectif, mais ne bloque pas la sortie. Sauvegarde lue (mon choix) : le `progress.sav`
  modifié le plus récemment, tous comptes et emplacements confondus.
- **Zones visitées** : si le drapeau du jeu n'est pas trouvé, l'outil mémorise lui-même les zones où il a vu Link (dans
  son cache local), plus la zone actuelle. Les zones déjà visitées avant l'installation apparaîtront au fil du jeu.
- **Compteurs et pourcentage** : les compteurs sont **par zone** ; le pourcentage porte sur **tout le jeu**. Un objet dont
  l'état ne peut pas être lu (par ex. quarts de cœur tant que le point 2 n'est pas résolu) est affiché sur la carte sans
  coche et **exclu** des compteurs et du pourcentage, plutôt que compté faux.
- **Coffres extérieurs** : `MapParam` n'en liste que 4 au premier niveau des cartes extérieures ; on affiche ce que
  `MapParam` liste, sans chercher d'autres sources en v1.
- **Vérification de version** : on compare le **build ID du code du jeu** (`e0f3cc…`). Une autre version de Hookshot
  est acceptée tant que la recherche de l'enregistrement de position réussit ; sinon, message clair et arrêt de la
  partie « direct » (la carte reste consultable sans position).
- **Cartes couvertes** : les 31 lieux du menu sont requis. Les cartes supplémentaires (sous-zones du château de Ganon,
  gymnase gerudo…) sont un bonus si leurs caméras de capture (30–35) s'associent sans difficulté.
- **Donjons** : la conversion n'a été vérifiée que sur des extérieurs, et l'empilement des calques
  `Main/Back/Grad/Alpha` n'a pas été étudié. **Première étape de la construction** : le vérifier sur un donjon, avant
  de figer le rendu des cartes.

## Laissé au constructeur

L'organisation du code, le format du cache local, le protocole de mise à jour des pages (SSE ou WebSocket), le port,
la gestion des erreurs et des cas où le jeu n'est pas lancé, et le détail visuel de la page tant qu'il reste dans le
style du jeu et la disposition A.

## Référence

Les scripts de l'étude (décodeurs BYML, BNTX, ASTC, lecteur mémoire, recherche de l'enregistrement de position) sont
dans [`research/`](../../../research/README.md) : point de départ du constructeur. Ils ne contiennent aucune donnée du jeu.
