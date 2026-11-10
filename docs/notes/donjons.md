# Cartes de donjon — constats (tâche 3)

Fichiers : `UI/CustomTex/Map/Dungeon/<Donjon>_<calque>.bntx.zs`, une texture chacun.

| Calque | Format | Contenu |
|---|---|---|
| `<Donjon>_All` | ASTC 6×6 | silhouette noire de tous les étages superposés (vue d'ensemble) ; absent pour le Temple de l'Esprit |
| `<Étage>_Back` | ASTC 6×6 | fond sombre de l'étage |
| `<Étage>_Main` ou `<Étage>_StateNN_Main` | ASTC 6×6 | dessin de l'étage ; les variantes `StateNN` sont des états du donjon (ex. Arbre Mojo 1F : toile intacte / percée) |
| `<Étage>_Alpha` / `_StateNN_Alpha` | RG8 non compressé, sélecteurs R,R,R,G | masque |
| `<Étage>_Grad` | BC4, sélecteurs R,R,R,1 | halos (taches lumineuses) |

Certains calques sont stockés en demi-résolution (1000×720) : on les agrandit à 2000×1440.

- **Projection** : la même que pour les extérieurs, avec l'échelle `2000 / Height` (et non `1440 / Height`).
  Vérifié : 136 coffres et Skulltulas sur 144 tombent sur un pixel dessiné de leur propre étage (94 %).
- **Étages** : `MapParam[<Donjon>].Floor` est rangé du plus bas au plus haut ; noms = niveaux à partir de `MinFloor`,
  sans niveau 0 (`MinFloor = -2`, `FloorNum = 5` → B2, B1, 1F, 2F, 3F). `TransY` = hauteur de l'étage.
- **Composition v1** : `Back` puis le dessin de l'étage par-dessus ; `Alpha` et `Grad` ne sont pas utilisés.
- **États** : l'état actuel du donjon n'est pas lu en v1 ; on montre le premier état (`State00`).
- **Correspondance caméra** : `MapCaptureInfo[i]` pour `MapMenuInfo[i]`, i = 20..29 (les 10 donjons).
