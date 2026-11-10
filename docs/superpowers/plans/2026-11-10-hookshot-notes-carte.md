# Hookshot Notes — carte interactive v1 : plan de construction

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** un `hookshot-notes.exe` posé dans le dossier Hookshot qui extrait les ressources de la copie du joueur, lance le jeu et sert une page web (téléphone / second écran) affichant la carte de la zone, la position de Link en direct et les objets à trouver, en modes Spoiler et Tracker.

**Architecture:** paquet Python `hookshot_notes` en quatre couches : `formats/` (lecture des fichiers du jeu), `extract/` (fabrique un cache local `world.json` + images à partir du `romfs`), `game/` (sauvegarde, lecture mémoire en direct), `server/` (HTTP + flux SSE, stdlib). La page `web/` (Leaflet en coordonnées pixel) consomme `world.json` et le flux d'état. `__main__.py` orchestre le premier lancement, le raccourci, le jeu et le navigateur ; PyInstaller emballe le tout.

**Tech Stack:** Python 3.12+ (testé en 3.14), `zstandard`, `Pillow`, `numpy`, `texture2ddecoder`, `mmh3`, `qrcode` ; stdlib `http.server` + `ctypes` ; Leaflet 1.9 (vendored, licence BSD-2) ; `pytest` ; PyInstaller.

**Spec:** [`docs/superpowers/specs/2026-11-10-hookshot-notes-carte-design.md`](../specs/2026-11-10-hookshot-notes-carte-design.md) — à lire avant toute tâche. Code de départ : [`research/`](../../../research/README.md).

## Global Constraints

- **Aucune ressource ni donnée du jeu dans le dépôt** : ni image, police, texte, liste d'objets ou position extraite. Les tests unitaires utilisent des données synthétiques fabriquées dans le test ; les tests qui lisent le vrai jeu sont marqués `@pytest.mark.game` et sautés si `HOOKSHOT_DIR` n'est pas défini.
- **Lecture seule** : le processus du jeu est ouvert avec `PROCESS_VM_READ | PROCESS_QUERY_INFORMATION` (`0x10 | 0x400`) uniquement ; aucun fichier du dossier Hookshot n'est modifié (on crée seulement `hookshot-notes-data/` et le raccourci).
- **Réseau local uniquement** : le serveur refuse toute IP cliente hors loopback et plages privées (`10/8`, `172.16/12`, `192.168/16`, `169.254/16`, `fe80::/10`, `fc00::/7`) ; aucune route ne modifie quoi que ce soit.
- **Version reconnue** : build ID du code du jeu (20 octets à l'offset `0x40` de `.hookshot_exefs/main`) = `e0f3ccfaf50065ae4ea01eb5aeb13b1a45da3348`.
- **Mémoire** : adresse Windows = `0x100000000000` + adresse Switch ; tas Switch à partir de `0x1000000000`.
- **Conversion monde → image** (image 2000×1440) : `px = 1000 + (x − CameraPos.X) × 1440 / Height`, `py = 720 + (z − CameraPos.Z) × 1440 / Height`.
- **Clé XOR des polices** : `a6 01 85 02` (période 4), données à partir de l'octet 8.
- **Textes de la page en français** ; noms de lieux tirés des textes du jeu dans la langue de `language.txt`.
- **Nom** : « Hookshot Notes » (raccourci « Hookshot Notes », exe `hookshot-notes.exe`, cache `hookshot-notes-data/`).

## Review Focus

1. **Le jeu n'est pas lancé, ou se ferme en pleine session** → la page reste utilisable (carte de la dernière zone, bandeau « Jeu non détecté »), puis se rebranche toute seule quand le jeu revient, en relançant la recherche de l'enregistrement. Test : Task 6 `test_tracker_survives_process_exit`.
2. **Link entre dans un intérieur ou une carte inconnue** (nom absent de `world.json`) → la page garde la dernière zone connue et masque la flèche, sans erreur. Test : Task 7 `test_unknown_map_keeps_last_zone`.
3. **Le téléphone perd la connexion** (Wi-Fi, écran verrouillé) → la page se reconnecte au flux et reprend l'état courant. Test : Task 7 `test_sse_sends_snapshot_on_connect`.
4. **Sauvegarde en cours d'écriture** (fichier tronqué) → on garde le dernier état « ramassé » valide au lieu de tout décocher. Test : Task 5 `test_truncated_save_keeps_previous`.
5. **Mauvaise version du jeu ou dossier incomplet** → message clair, aucun cache partiel laissé (extraction dans un dossier temporaire puis renommage). Test : Task 4 `test_extract_is_atomic`, Task 9 `test_wrong_build_id_message`.

---

## Structure des fichiers

```
pyproject.toml                    dépendances, pytest (marqueur game)
hookshot_notes/
  __init__.py                     __version__ = "0.1.0"
  __main__.py                     lancement (Task 9)
  paths.py                        GameDir : chemins du dossier Hookshot (Task 1)
  formats/
    sarc.py   byml.py   zs.py     (Task 1)
    bntx.py   texture.py   font.py   nso.py   (Task 2)
  extract/
    dungeon.py                    composition des étages (Task 3)
    world.py   assets.py   run.py (Task 4)
  game/
    gamedata.py   save.py         (Task 5)
    memory.py   live.py           (Task 6)
  server/
    state.py   http.py            (Task 7)
  web/
    index.html  app.js  style.css  vendor/leaflet/   (Task 8)
  launcher/
    shortcut.py   qr.py   game.py (Task 9)
tests/
  conftest.py                     fixture game_dir (saute si HOOKSHOT_DIR absent)
  test_formats.py  test_texture.py  test_dungeon.py  test_world.py
  test_save.py  test_live.py  test_server.py  test_launcher.py
packaging/hookshot-notes.spec     PyInstaller (Task 9)
```

---

### Task 1: Squelette, SARC, BYML, décompression `.zs`

**Files:**
- Create: `pyproject.toml`, `hookshot_notes/__init__.py`, `hookshot_notes/paths.py`, `hookshot_notes/formats/{__init__,sarc,byml,zs}.py`, `tests/conftest.py`, `tests/test_formats.py`, `.gitignore` (`hookshot-notes-data/`, `__pycache__/`, `dist/`, `build/`, `.superpowers/`)

**Interfaces:**
- Produces:
  - `paths.GameDir(root: Path)` avec attributs `romfs`, `exefs_main` (`.hookshot_exefs/main`), `launcher` (`hookshot.exe`), `saves` (`user/save`), `language_file` (`language.txt`) ; `GameDir.find(start: Path) -> GameDir | None` (remonte depuis `start` jusqu'à trouver `romfs/` + `.hookshot_exefs/`).
  - `sarc.read_sarc(buf: bytes) -> dict[str, bytes]`
  - `byml.parse_byml(buf: bytes) -> Any` (dict/list/str/int/float/bool/None/bytes ; nœuds `0x20`/`0x21` → `dict[int, Any]`), gère `YB` et `BY`.
  - `zs.ZsReader(romfs: Path)` ; `.read(rel: str) -> bytes` (sans `.zs` → lecture brute ; avec → dictionnaire choisi par l'ID de trame, aucun si ID 0) ; `ZsReader.from_dicts(romfs: Path, dicts: dict[str, bytes]) -> ZsReader` (dictionnaires fournis au lieu de `Pack/ZsDic.pack.zs`, pour les tests).
  - `tests/conftest.py` : fixture `game_dir` (`GameDir` depuis `HOOKSHOT_DIR`, sinon `pytest.skip`) ; marqueur `game` déclaré dans `pyproject.toml`.

- [ ] **Step 1: Write the failing tests** dans `tests/test_formats.py` :
  - `test_byml_little_and_big_endian` : construit dans le test un BYML v7 minimal (racine dict `{"a": 1, "b": [True, "x"]}`) en `YB` puis en `BY` et vérifie que `parse_byml` rend le même dict.
  - `test_byml_hash32_dict` : nœud `0x20` avec deux clés u32 → `{0x11223344: 5, 0xAABBCCDD: 6}`.
  - `test_sarc_roundtrip` : SARC fabriqué dans le test avec `"a/b.txt" -> b"hi"`, `"c" -> b""` → `read_sarc` rend ces deux entrées.
  - `test_zs_picks_dictionary_by_id` : compresse `b"x"*100` avec un dictionnaire entraîné dans le test (`zstandard.train_dictionary`) et sans dictionnaire ; un `ZsReader` dont on injecte les dictionnaires (`ZsReader.from_dicts(romfs, {name: bytes})`) relit les deux.
  - `@pytest.mark.game test_gamedatalist_shape(game_dir)` : `parse_byml(ZsReader(game_dir.romfs).read("GameData/GameDataList.Product.110.byml.zs"))["Data"]` contient les clés `Bool64bitKey` et `Vector3`.
- [ ] **Step 2:** `pytest tests/test_formats.py -v` → FAIL (modules absents).
- [ ] **Step 3: Implement** en reprenant `research/byml.py`, `research/zs.py` (sans chemins en dur ; dictionnaires lus dans `Pack/ZsDic.pack.zs` via `read_sarc`), plus `paths.py`.
- [ ] **Step 4:** `pytest tests/test_formats.py -v` → PASS (le test `game` passe avec `HOOKSHOT_DIR=C:\chemin\vers\Hookshot`).
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: lecture SARC, BYML et .zs"`

### Task 2: Textures BNTX (Switch 2), polices, build ID

**Files:**
- Create: `hookshot_notes/formats/{bntx,texture,font,nso}.py`, `tests/test_texture.py`

**Interfaces:**
- Consumes: `ZsReader` (Task 1).
- Produces:
  - `bntx.TexInfo` (dataclass : `name, fmt, width, height, block_height_log2, data_offset, data_size, comp_sel`) ; `bntx.list_textures(buf: bytes) -> dict[str, TexInfo]`.
  - `texture.swizzle(linear: bytes, bw: int, bh: int, bpb: int, bhl: int, size: int) -> bytes` et `texture.deswizzle(raw: bytes, bw: int, bh: int, bpb: int, bhl: int) -> bytes` (GOB Tegra avec bits 5/6 échangés, comme `research/tex.py` avec `swap56=True`).
  - `texture.decode(buf: bytes, info: TexInfo) -> PIL.Image.Image` (RGBA, rognée à `width×height`) ; formats : BC4 `0x1d`, ASTC `0x2d..0x34` (blocs 4×4, 5×4, 5×5, 6×5, 6×6, 8×5, 8×6, 8×8) ; une texture BC4 devient blanc + alpha.
  - `font.decrypt(buf: bytes) -> bytes` (OpenType en clair).
  - `nso.build_id(main: Path) -> str` (hex des 20 octets à `0x40`).
- [ ] **Step 1: Write the failing tests** :
  - `test_swizzle_roundtrip` : données aléatoires `bw=13, bh=9, bpb=16, bhl=2`, taille = adresse max + 1 calculée par la fonction → `deswizzle(swizzle(x)) == x`.
  - `test_font_decrypt` : chiffre dans le test un faux OTF `b"OTTO" + b"\x00"*60` (en-tête 8 octets + XOR) → `decrypt` rend l'original.
  - `test_build_id` : fichier temporaire avec 20 octets connus à `0x40` → hex attendu.
  - `@game test_field_map_decodes(game_dir)` : `KokiriForest_Child_00` → image 2000×1440, au moins 30 % de pixels avec alpha > 0.
  - `@game test_real_build_id(game_dir)` → `"e0f3ccfaf50065ae4ea01eb5aeb13b1a45da3348"`.
- [ ] **Step 2:** `pytest tests/test_texture.py -v` → FAIL.
- [ ] **Step 3: Implement** à partir de `research/bntx.py` et `research/tex.py` ; vectoriser `deswizzle` avec numpy (calcul des adresses une fois par forme `(bw, bh, bpb, bhl)` puis indexation) : une carte 2000×1440 doit se décoder en moins de 3 s.
- [ ] **Step 4:** `pytest tests/test_texture.py -v` → PASS.
- [ ] **Step 5: Commit** — `feat: textures BNTX Switch 2, polices, build ID`

### Task 3: Vérifier et composer les cartes de donjon (étape de recherche)

La spec demande de vérifier les donjons avant de figer le rendu. Cette tâche établit, par un test automatique, la conversion et l'empilement des calques.

**Files:**
- Create: `hookshot_notes/extract/dungeon.py`, `tests/test_dungeon.py`, `docs/notes/donjons.md` (constats : ordre des calques, rôle de `Grad`/`Alpha`/`Back`, variantes `StateNN`)

**Interfaces:**
- Consumes: `ZsReader`, `parse_byml`, `list_textures`, `decode`.
- Produces:
  - `dungeon.floor_layers(romfs_names: list[str], dungeon: str) -> dict[str, dict[str, str]]` : étage (`"1F"`, `"B1"`…) → rôle (`"Main"`, `"Back"`, `"Grad"`, `"Alpha"`, `"State00_Main"`…) → nom de fichier.
  - `dungeon.compose_floor(layers: dict[str, PIL.Image.Image], state: str | None) -> PIL.Image.Image` (2000×1440 RGBA).
  - `dungeon.floor_for_height(floors: list[dict], y: float) -> int` : index de l'étage dont `TransY` est le plus grand ≤ `y` (le plus bas si `y` est sous tous).
- [ ] **Step 1: Write the failing tests** :
  - `test_floor_for_height` : `TransY` `[0, 10, 20]` → `y=15 → 1`, `y=-5 → 0`, `y=99 → 2`.
  - `@game test_dungeon_objects_on_floor(game_dir)` : pour chaque donjon des 10 du menu (`MapMenuInfo` 20–29, caméra de même index), pour chaque `Floor[i]`, au moins 90 % des `TBox` et `CollectSign` de cet étage tombent sur un pixel d'alpha > 0 de `compose_floor(...)` de cet étage, avec la formule globale.
  - `@game test_field_objects_on_map(game_dir)` : même critère (≥ 90 %) pour les 20 extérieurs, enfant et adulte, objets du premier niveau de `MapParam`.
- [ ] **Step 2:** `pytest tests/test_dungeon.py -v` → FAIL.
- [ ] **Step 3: Investigate then implement** : décoder les calques d'un donjon (Arbre Mojo), les regarder, décider l'ordre d'empilement (hypothèse de départ : `Back` en dessous, `Main` au-dessus, `Alpha` comme masque, `Grad` en dégradé multiplié), l'écrire dans `docs/notes/donjons.md`, puis implémenter. Si la formule ne colle pas pour les donjons, noter l'écart (décalage, échelle, axe) dans la même note et l'appliquer dans `extract/world.py` (Task 4) via une correction par donjon.
- [ ] **Step 4:** `pytest tests/test_dungeon.py -v` → PASS.
- [ ] **Step 5: Commit** — `feat: composition des étages de donjon vérifiée`

### Task 4: Extraction du monde vers le cache local

**Files:**
- Create: `hookshot_notes/extract/{world,assets,run}.py`, `tests/test_world.py`

**Interfaces:**
- Consumes: Tasks 1–3.
- Produces:
  - `run.extract(game: GameDir, out: Path, progress: Callable[[str, float], None]) -> None` : écrit dans `out.with_suffix(".tmp")` puis renomme en `out` (rien de partiel si erreur) ; écrit `out/meta.json = {"build_id": str, "format": 1}`.
  - `run.cache_is_valid(out: Path, build_id: str) -> bool`.
  - Contenu de `out/` : `world.json`, `maps/<zone>_<age>.webp` (extérieurs, qualité 85), `maps/<donjon>_<etage>[_<state>].webp`, `icons/<nom>.png`, `ui/<nom>.png`, `fonts/cetra.otf`, `fonts/clarimo.otf`.
  - Schéma de `world.json` (consommé par Tasks 7 et 8) :
    ```json
    {"zones": [{"id": "KokiriForest", "name": "Forêt Kokiri", "kind": "field|dungeon",
                "maps": {"KokiriForest_Child": {"age": "child", "image": "maps/KokiriForest_child.webp"}},
                "floors": [{"name": "1F", "transY": 0.0, "image": "maps/InsideTheDekuTree_1F.webp"}],
                "camera": {"x": -5.0, "z": -12.0, "height": 300.0},
                "objects": [{"id": "9623998892552467148", "type": "skulltula|chest|heart|place|exit",
                              "map": "KokiriForest_Child", "floor": null, "px": 1110.2, "py": 868.0,
                              "icon": "MapIconCollectSkullSign_00", "label": "", "flag": "bool64"}]}],
     "bancToZone": {"KokiriForest_Child": "KokiriForest"},
     "image": {"width": 2000, "height": 1440}}
    ```
    `id` en chaîne (u64 dépasse les entiers sûrs en JS). `flag` vaut `"bool64"` pour coffres et Skulltulas, `null` sinon (état illisible → exclu des compteurs, spec). `type` : `TBox→chest`, `CollectSign*→skulltula`, `CollectHeart*→heart`, `Facility→place`, `EntranceAnchor→exit` (avec `label` = nom de la destination). Les listes `*All` et non-`All` sont fusionnées par `id`. Icône de `place` choisie par `IconType` (table dans `world.py`, inconnu → `MapIconShopGeneral_00`).
  - `name` : texte du lieu lu dans `Mals/<langue>.Product.110.sarc.zs` → `LocationMsg/Location.msbt` (correspondance langue `language.txt` → préfixe `EUfr`, `USen`, … dans `world.py`) ; repli sur l'`id`.
- [ ] **Step 1: Write the failing tests** :
  - `test_extract_is_atomic(tmp_path)` : `run.extract` avec un `GameDir` dont le `romfs` est vide → lève une erreur et `out` n'existe pas, ni `out.tmp`.
  - `@game test_world_contents(game_dir, tmp_path)` : après `extract`, `world.json` a 31 zones du menu (au moins), `bancToZone["KokiriForest_Child"] == "KokiriForest"`, 3 Skulltulas dans les objets de `KokiriForest_Child`, chaque objet a `0 ≤ px < 2000` et `0 ≤ py < 1440`, toutes les images citées existent, `cache_is_valid(out, build_id)` est vrai.
- [ ] **Step 2:** `pytest tests/test_world.py -v` → FAIL.
- [ ] **Step 3: Implement** ; icônes et décors : ceux de la section « Objets » de la spec (`MapIcon*`, `MapLocationNameBgFill_00`, `MapLocationNameBgOutline_00`, `LocationDecoLine_00`) depuis `UI/Layout2Archive/Common.Product.100.Nin_Ounce_NVN2.bntx.zs` ; polices `Font2/Scalable/CetraDisplayPro-Medium…` et `ClarimoUDPE-DemiBold…` via `font.decrypt`.
- [ ] **Step 4:** `pytest tests/test_world.py -v` → PASS ; extraction complète < 5 min.
- [ ] **Step 5: Commit** — `feat: extraction du monde et des ressources`

### Task 5: Drapeaux de partie et lecture de la sauvegarde

**Files:**
- Create: `hookshot_notes/game/{gamedata,save}.py`, `tests/test_save.py`, `docs/notes/sauvegarde.md`

**Interfaces:**
- Produces:
  - `gamedata.flag_hash(name: str) -> int` (MurmurHash3 32 bits, graine 0, non signé).
  - `save.find_latest_save(saves: Path) -> Path | None` (le `progress.sav` modifié le plus récemment, tous comptes et emplacements).
  - `save.SaveReader()` ; `.read(path: Path) -> SaveState | None` ; garde le dernier état valide et le rend si le fichier est tronqué ou illisible.
  - `save.SaveState` (dataclass) : `collected: frozenset[int]` (clés `Bool64bitKey` vraies), `life: int`, `max_life: int`, `mtime: float`.
- [ ] **Step 1: Write the failing tests** :
  - `test_flag_hash_known_values` : `flag_hash("PlayerStatus.Life") == 833312128`, `flag_hash("PlayerStatus.SavePos") == 3364127117`.
  - `test_find_latest_save(tmp_path)` : trois `progress.sav` avec des `mtime` différents → le plus récent.
  - `test_truncated_save_keeps_previous(tmp_path)` : un `SaveReader` lit une sauvegarde synthétique valide puis un fichier tronqué à 10 octets → le second `read` rend le même `SaveState` que le premier.
  - `@game test_real_save_life(game_dir)` : la dernière sauvegarde a `life > 0` et `max_life >= life`.
- [ ] **Step 2:** `pytest tests/test_save.py -v` → FAIL.
- [ ] **Step 3: Investigate the `Bool64bitKey` section** : avec le porteur du projet, ramasser une Skulltula ou ouvrir un coffre dont l'`InstanceID` est connu, sauvegarder, comparer les deux `progress.sav` (avant/après), et trouver comment la clé u64 est rangée. Décrire le format dans `docs/notes/sauvegarde.md`, puis écrire la sauvegarde synthétique du test selon ce format.
- [ ] **Step 4: Implement** `save.py` (vie et vie max via `flag_hash` comme dans l'étude : paire hash/valeur alignée sur 8 octets).
- [ ] **Step 5:** `pytest tests/test_save.py -v` → PASS ; vérification manuelle : l'`InstanceID` ramassé à l'étape 3 est dans `collected`.
- [ ] **Step 6: Commit** — `feat: lecture de la sauvegarde (vie, objets ramassés)`

### Task 6: Lecture mémoire en direct

**Files:**
- Create: `hookshot_notes/game/{memory,live}.py`, `tests/test_live.py`

**Interfaces:**
- Produces:
  - `memory.Memory` (protocole) : `read(guest: int, n: int) -> bytes | None`, `regions(lo: int, hi: int) -> Iterator[tuple[int, int]]`.
  - `memory.ProcessMemory(pid: int)` (implémente `Memory` via `ctypes`, droits `0x10 | 0x400`) ; `memory.find_game_pid() -> int | None` (processus `hookshot.exe` dont le chemin est sous `bin\` du dossier Hookshot).
  - `live.find_record(mem: Memory, banc_names: set[str]) -> int | None` : adresse Switch du `vec3` ; motif = `[u64 ptr = adresse du texte][u32 0x40][texte 64 o, nom ∈ banc_names][8 octets nuls][3 float finis, |v| < 5000]`, recherche dans `[0x1000000000, 0x1200000000)` par blocs de 64 Mio ; si plusieurs candidats, garder celui dont la position n'est pas `(0,0,0)`.
  - `live.LiveState` (dataclass) : `banc: str`, `x: float`, `y: float`, `z: float`, `t: float`.
  - `live.Tracker(open_memory: Callable[[], Memory | None], banc_names: set[str])` ; `.poll() -> LiveState | None` : ouvre/rouvre la mémoire si besoin, cherche l'enregistrement si inconnu, le relit, et l'oublie (nouvelle recherche au prochain appel) si la lecture échoue ou si le nom n'est plus du bon format ; `.status -> Literal["no_game", "searching", "live"]`.
- [ ] **Step 1: Write the failing tests** avec un `FakeMemory` (dict de régions en mémoire, dans le test) :
  - `test_find_record_pattern` : une région contenant un faux enregistrement `KokiriForest_Child` + `(1.0, 2.0, 3.0)` et un leurre à `(0,0,0)` → adresse du vrai `vec3`.
  - `test_rejects_wrong_capacity_and_unknown_name` : capacité `0x20` ou nom hors `banc_names` → `None`.
  - `test_tracker_follows_zone_change` : le faux enregistrement passe à `HyruleField_Child` → `poll()` rend la nouvelle carte sans nouvelle recherche.
  - `test_tracker_survives_process_exit` : `open_memory` rend `None` → `status == "no_game"` et `poll() is None` ; puis rend un `FakeMemory` dont l'enregistrement est à une autre adresse → `status == "live"` avec la bonne position.
- [ ] **Step 2:** `pytest tests/test_live.py -v` → FAIL.
- [ ] **Step 3: Implement** à partir de `research/mem.py` et `research/locate.py`.
- [ ] **Step 4:** `pytest tests/test_live.py -v` → PASS.
- [ ] **Step 5: Manual check (jeu lancé)** : `python -m hookshot_notes.game.live` (petit `__main__` qui affiche `poll()` deux fois par seconde) → la carte et la position changent quand Link bouge et quand il change de zone ; la recherche prend moins de 15 s.
- [ ] **Step 6: Commit** — `feat: position et carte de Link en direct`

### Task 7: Serveur (état, HTTP, flux)

**Files:**
- Create: `hookshot_notes/server/{state,http}.py`, `tests/test_server.py`

**Interfaces:**
- Consumes: `world.json` (Task 4), `SaveReader`/`find_latest_save` (Task 5), `Tracker` (Task 6).
- Produces:
  - `state.StateHub(world: dict, data_dir: Path)` ; `.update(live: LiveState | None, status: str, save: SaveState | None) -> dict | None` (rend le nouvel instantané s'il a changé) ; `.snapshot() -> dict`. Instantané :
    `{"status": "no_game|searching|live", "zone": "KokiriForest", "banc": "KokiriForest_Child", "floor": 0|null, "player": {"px": float, "py": float} | null, "collected": ["<id>", …], "visited": ["KokiriForest", …], "percent": float}`.
    Zone inconnue (`banc` absent de `bancToZone`) → `zone`/`banc` gardent la dernière valeur connue et `player = null`. `visited` = zones vues par l'outil, persistées dans `data_dir/visited.json`. `percent` = objets `flag="bool64"` ramassés / total des objets `flag="bool64"` × 100.
  - `http.serve(hub: StateHub, data_dir: Path, web_dir: Path, port: int) -> ThreadingHTTPServer` (port 0 = libre) : `GET /` → `web/index.html` ; `/web/*` ; `/data/*` (fichiers du cache) ; `/api/world` ; `/api/state` ; `/events` (SSE : instantané complet à la connexion puis à chaque changement, `: ping` toutes les 15 s) ; tout le reste → 404 ; IP non locale → 403 (Global Constraints).
  - `http.lan_url(port: int) -> str` (`http://<ip LAN>:<port>/`, IP de l'interface qui sort vers `8.8.8.8` sans envoyer de paquet).
  - Mode démo : `state.DemoSource(world: dict, banc: str)` qui rend des `LiveState` en cercle dans la zone donnée (pour tester la page sans le jeu).
- [ ] **Step 1: Write the failing tests** (petit `world` synthétique dans le test) :
  - `test_percent_counts_only_readable` : 2 objets `bool64` dont 1 ramassé + 1 cœur `flag=null` → `percent == 50.0`.
  - `test_unknown_map_keeps_last_zone` : live `KokiriForest_Child` puis `Link_House_Child` (inconnu) → `zone == "KokiriForest"`, `player is None`.
  - `test_visited_persists(tmp_path)` : deux zones vues, nouveau `StateHub` sur le même dossier → `visited` contient les deux.
  - `test_sse_sends_snapshot_on_connect` : serveur sur port 0, lecture de `/events` → premier message `data:` = `json.dumps(hub.snapshot())`.
  - `test_rejects_non_local_client` : la fonction de contrôle d'IP refuse `8.8.8.8` et accepte `192.168.1.20` et `127.0.0.1`.
  - `test_no_path_traversal` : `GET /data/../pyproject.toml` → 404.
- [ ] **Step 2:** `pytest tests/test_server.py -v` → FAIL.
- [ ] **Step 3: Implement** ; boucle de fond : `Tracker.poll()` toutes les 250 ms, `SaveReader.read(find_latest_save())` quand le `mtime` change, diffusion SSE des instantanés changés.
- [ ] **Step 4:** `pytest tests/test_server.py -v` → PASS.
- [ ] **Step 5: Commit** — `feat: serveur local et flux d'état`

### Task 8: Page carte (style Zelda, disposition A)

**Files:**
- Create: `hookshot_notes/web/{index.html,app.js,style.css}`, `hookshot_notes/web/vendor/leaflet/` (Leaflet 1.9.4 : `leaflet.js`, `leaflet.css`, `LICENSE`)

**Interfaces:**
- Consumes: `/api/world`, `/events`, `/data/*` (Task 7).
- Produces: la page. Comportements requis (spec) :
  - Leaflet en `L.CRS.Simple`, image de la zone en `imageOverlay` sur `[[0,0],[1440,2000]]` (y vers le bas : `latlng = [-py, px]` ou équivalent cohérent), zoom/glisser au doigt.
  - Ruban du nom de lieu (masques `ui/MapLocationNameBgFill_00.png` / `…Outline_00.png`, police `fonts/cetra.otf`) ; compteurs de zone en haut à droite ; filtres en bas (Skulltulas, coffres, cœurs, lieux, sorties) ; bouton recentrer avec `icons/MapIconPlayer_00.png`.
  - Flèche de Link `MapIconPlayer_00` animée entre deux positions (interpolation sur la durée entre deux messages) et tournée selon la direction du dernier déplacement (orientation du jeu non disponible, spec point 4).
  - Suivi : la carte suit Link et change d'image au changement de `banc` ; un glisser manuel coupe le suivi jusqu'au bouton recentrer.
  - Donjon : sélecteur d'étage, positionné par défaut sur `snapshot.floor`.
  - Modes **Spoiler** / **Tracker** (interrupteur, mémorisé dans `localStorage`) : Spoiler = tous les objets, ramassés en icône `…Check_00` ; Tracker = seulement les ramassés, compteurs sans total.
  - Zones non visitées : non sélectionnables depuis le menu des zones ; la zone courante l'est toujours.
  - Bandeau « Jeu non détecté » / « Recherche de Link… » selon `status`.
  - Reconnexion automatique du flux (EventSource + reprise sur `onerror` après 2 s).
- [ ] **Step 1: Démarrer en mode démo** : `python -m hookshot_notes --demo KokiriForest_Child --no-game` (option ajoutée en Task 9 ; d'ici là, un petit script `tests/manual/demo_server.py` qui lance `serve` avec `DemoSource`).
- [ ] **Step 2: Implement** la page.
- [ ] **Step 3: Verify in the browser pane** (desktop puis preset mobile 375×812) : la flèche tourne en cercle et glisse sans saut ; les 3 Skulltulas de la forêt Kokiri sont aux mêmes endroits que sur la maquette validée ; Tracker cache les non-ramassés ; glisser coupe le suivi, le bouton recentre ; couper le serveur affiche le bandeau, le relancer reprend sans recharger.
- [ ] **Step 4: Commit** — `feat: page carte style Zelda`

### Task 9: Lanceur, raccourci, QR code, exe

**Files:**
- Create: `hookshot_notes/__main__.py`, `hookshot_notes/launcher/{shortcut,qr,game}.py`, `tests/test_launcher.py`, `packaging/hookshot-notes.spec`, `README.md` (installation : poser l'exe dans le dossier Hookshot, double-cliquer ; rappel qu'aucune ressource du jeu n'est fournie)
- Modify: `hookshot_notes/server/http.py` (route `GET /api/qr`), `hookshot_notes/web/index.html` + `app.js` (QR affiché sur la page du PC seulement, c.-à-d. quand l'hôte est `localhost`)

**Interfaces:**
- Consumes: tout le reste.
- Produces:
  - `game.check_version(game: GameDir) -> str | None` : `None` si le build ID est reconnu, sinon le message « Version du jeu non reconnue (build <id>). Hookshot Notes fonctionne avec la mise à jour 2.0.0. La carte reste consultable sans position en direct. »
  - `game.ensure_running(game: GameDir) -> None` : lance `game.launcher` (`subprocess.Popen`, dossier de travail = dossier Hookshot) si `find_game_pid()` ne trouve rien.
  - `shortcut.create_desktop_shortcut(target: Path, name: str = "Hookshot Notes") -> Path` (PowerShell + `WScript.Shell`, ne remplace pas un raccourci existant).
  - `qr.svg(url: str) -> str` (via `qrcode`, sortie SVG).
  - CLI `python -m hookshot_notes [--port N] [--no-game] [--demo BANC] [--game-dir PATH]` : trouve le dossier (dossier de l'exe, sinon `--game-dir`) ; extrait si `cache_is_valid` est faux (progression affichée) ; crée le raccourci au premier lancement ; démarre le serveur (port 8737 par défaut, sinon libre) ; ouvre `http://localhost:<port>/` sur le PC ; lance le jeu sauf `--no-game`. La page PC affiche `qr.svg(lan_url(port))` (`GET /api/qr`, à ajouter dans `server/http.py`).
- [ ] **Step 1: Write the failing tests** :
  - `test_wrong_build_id_message(tmp_path)` : faux `main` avec un autre build ID → message qui contient « non reconnue ».
  - `test_shortcut_command_quotes_paths` : la commande PowerShell générée pour un chemin avec espaces et apostrophe est correctement échappée (tester la fonction qui construit la commande, sans l'exécuter).
  - `test_qr_svg` : `qr.svg("http://192.168.1.5:8737/")` commence par `<svg` ou `<?xml`.
- [ ] **Step 2:** `pytest tests/test_launcher.py -v` → FAIL.
- [ ] **Step 3: Implement** ; PyInstaller en un fichier (`--onefile`, inclut `hookshot_notes/web/`) dans `packaging/hookshot-notes.spec`.
- [ ] **Step 4:** `pytest -v` → tout PASS (tests `game` compris avec `HOOKSHOT_DIR`).
- [ ] **Step 5: Manual end-to-end** : `pyinstaller packaging/hookshot-notes.spec`, copier `dist/hookshot-notes.exe` dans `C:\chemin\vers\Hookshot`, double-clic → extraction, raccourci « Hookshot Notes » sur le Bureau, page ouverte avec QR, jeu lancé ; scanner le QR depuis le téléphone ; charger une sauvegarde et marcher → la flèche suit sur le téléphone ; changer de zone → la carte change.
- [ ] **Step 6: Commit** — `feat: lanceur, raccourci et exe`
