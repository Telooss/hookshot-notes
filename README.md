# Hookshot Notes

Carte interactive en direct pour **Ocarina of Time** (remake Switch 2) joué avec **Hookshot** sur PC — à ouvrir sur ton
téléphone ou sur un second écran, comme les cartes interactives de Breath of the Wild / Tears of the Kingdom.

- La carte de la zone où tu te trouves, dans le style du jeu, avec la position de Link en direct.
- Les Skulltulas d'or, coffres, quarts de cœur, boutiques et sorties de la zone.
- **Mode Spoiler** (tout ce qu'il reste à trouver) ou **mode Tracker** (seulement ce que tu as déjà trouvé).
- Pourcentage de complétion, étages des donjons, lieux visités.

## Installation

1. Télécharge `hookshot-notes.exe` (page Releases).
2. Pose-le dans ton dossier Hookshot (celui qui contient `romfs` et `hookshot.exe`).
3. Double-clique dessus. La première fois, il prépare les cartes à partir de **ta** copie du jeu (environ une minute)
   et crée un raccourci **Hookshot Notes** sur le Bureau. Ensuite, utilise ce raccourci : il lance le jeu et la carte.
4. Une page s'ouvre sur le PC avec un **QR code** : scanne-le avec ton téléphone (même Wi-Fi).

Laisse la fenêtre de Hookshot Notes ouverte pendant que tu joues.

## Ce que fait (et ne fait pas) Hookshot Notes

- **Aucune ressource de Nintendo n'est fournie** : cartes, icônes, polices et textes sont extraits de ta copie du jeu,
  sur ta machine, dans `hookshot-notes-data/`.
- **Lecture seule** : l'outil lit la mémoire du jeu et ta sauvegarde, il n'écrit jamais dedans et ne modifie pas Hookshot.
- **Réseau local uniquement** : la page n'est accessible que depuis ton réseau.
- Version prise en charge : jeu en mise à jour **2.0.0**. Pour une autre version, la carte reste consultable mais sans
  position en direct.
- Les coches (objets ramassés) se mettent à jour quand le jeu sauvegarde.

## Développement

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e .[dev]
HOOKSHOT_DIR="C:/chemin/vers/Hookshot" .venv/Scripts/python -m pytest      # tests "game" : lisent ta copie du jeu
.venv/Scripts/python -m hookshot_notes --game-dir "C:/chemin/vers/Hookshot" --demo KokiriForest_Child --no-game
.venv/Scripts/pyinstaller packaging/hookshot-notes.spec                     # dist/hookshot-notes.exe
```

Conception : [`docs/superpowers/specs/`](docs/superpowers/specs/) · notes de format : [`docs/notes/`](docs/notes/).
Carte : [Leaflet](https://leafletjs.com) (BSD-2, `hookshot_notes/web/vendor/leaflet/LICENSE`).

*Projet de fans, non affilié à Nintendo.*
