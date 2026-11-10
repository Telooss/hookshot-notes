# Format de `progress.sav` — constats (tâche 5)

Fichier : `user/save/<compte>/slot_NN/progress.sav`, petit-boutiste.

| Offset | Contenu |
|---|---|
| `0x00` | magie `04 03 02 01` |
| `0x04` | version |
| `0x08` | u32 : fin de la table hash/valeur |
| `0x28` | table de paires `(u32 hash, u32 valeur)` jusqu'à la fin de table |

- Les paires sont groupées par type ; une paire `(0, n)` marque le début du type n (0 Bool, 2 Int, 4 Float, …).
- Pour les types simples (Bool, Int, UInt, Float, Enum), la valeur est dans la paire ; pour les autres (tableaux,
  vecteurs, chaînes), la valeur est un offset dans le fichier.
- Les hashs sont MurmurHash3 32 bits des noms de drapeaux (`PlayerStatus.Life`…).
- **Drapeaux `Bool64bitKey`** (coffres ouverts, Skulltulas prises… : clé = `InstanceID` de l'objet) : la dernière paire
  de la table est `(2749067540, offset)` — 2749067540 est le `SaveTypeHash` de `progress.sav` dans
  `GameDataList`/`MetaData`. À cet offset commence un tableau **trié** de clés u64, celles des drapeaux à vrai,
  terminé par 8 octets nuls (fin du fichier). Vu dans les 6 emplacements de sauvegarde (34 à 40 clés).
- Reste à confirmer en jeu : qu'une Skulltula ramassée apparaît bien dans ce tableau (vérification de bout en bout, tâche 9).
