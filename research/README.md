# Scripts de l'étude (référence)

Scripts jetables écrits pendant l'étude de faisabilité. Ils ne contiennent aucune donnée du jeu ; ils lisent la copie
locale du joueur. Les chemins (`C:/chemin/vers/Hookshot/...`) sont en dur : à adapter.

Dépendances : `zstandard`, `pillow`, `numpy`, `texture2ddecoder`, `mmh3`.

| Fichier | Rôle |
|---|---|
| `zs.py` | décompression des `.zs` (dictionnaires de `Pack/ZsDic.pack.zs`, choix du dictionnaire par ID de trame) |
| `byml.py` | lecteur BYML v2–v7, petit et gros-boutiste |
| `bntx.py` | liste des textures d'un BNTX « Ounc » (format, taille, position des données) |
| `tex.py` | (dé)rangement des pixels Tegra avec l'échange des bits 5/6 du Switch 2, décodage BC4/ASTC |
| `maptest.py` | place les objets de `MapParam` sur une carte via `MapCaptureInfo` (vérification de la conversion) |
| `mem.py` | lecture seule de la mémoire du jeu (`0x100000000000` + adresse Switch) |
| `find_pos.py` | cherche la position de sauvegarde (`PlayerStatus.SavePos`) dans la mémoire |
| `locate.py` | retrouve l'enregistrement « carte actuelle + position » par son motif |
| `sample2.py` | enregistre plusieurs positions candidates pour comparer leur fréquence de mise à jour |
