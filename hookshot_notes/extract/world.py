"""world.json: zones, their maps/floors and the objects to show, from the player's romfs."""
from ..formats.byml import parse_byml
from ..formats.msbt import read_msbt
from ..formats.sarc import read_sarc
from ..formats.zs import ZsReader
from .dungeon import floor_names
from .projection import IMAGE_H, IMAGE_W, project

MENU_ZONES = 30  # MapMenuInfo 0..19 fields, 20..29 dungeons; entry 30 repeats the adult Hyrule Castle map

LANGUAGES = {"fr": "EUfr", "fr-CA": "USfr", "en-US": "USen", "en-GB": "EUen", "de": "EUde", "it": "EUit",
             "es": "EUes", "es-419": "USes", "pt-BR": "USpt", "nl": "EUnl", "pl": "EUpl", "ru": "EUru",
             "ja": "JPja", "ko": "KRko", "zh-Hans": "CNzh", "zh-Hant": "TWzh"}

PLACE_ICONS = {
    1: "MapIconShopMask_00", 3: "MapIconTraining_00", 4: "MapIconShopBombchu_00", 5: "MapIconMiniGameDampe_01",
    6: "MapIconMiniGameFrog_00", 7: "MapIconMiniGameArchery_00", 8: "MapIconMiniGameCocco_00",
    9: "MapIconMiniGameEpona_00", 11: "MapIconGreatFairy_00", 13: "MapIconKokiriShop_00", 14: "MapIconGoronShop_00",
    15: "MapIconZolaShop_00", 16: "MapIconShopMedicine_00", 17: "MapIconShopMedicine_00", 18: "MapIconShopGeneral_00",
    19: "MapIconShopGeneral_00", 20: "MapIconMiniGameTarget_00", 21: "MapIconMiniGameTarget_00",
    22: "MapIconMiniGameBowling_00", 23: "MapIconShopTreasure_00", 26: "MapIconMiniGameDampe_00",
    27: "MapIconMiniGameDiving_00", 28: "MapIconMiniGameFishing_00", 29: "MapIconObaba_00", 30: "MapIconGhostShop_00",
    31: "MapIconSkullKid_00", 32: "MapIconRunningRace_00", 33: "MapIconSurfaceFair_00", 34: "MapIconMagicBean_00",
    35: "MapIconCarpenter_00", 36: "MapIconCarpenter_01", 37: "MapIconCarpenter_02", 38: "MapIconCarpenter_03",
}
PLACE_DEFAULT = "MapIconSign_00"

# MapParam list -> (object type, icon, readable flag)
KINDS = {
    "TBox": ("chest", "MapIconTreasure_00", "bool64"),
    "CollectSign": ("skulltula", "MapIconCollectSkullSign_00", "bool64"),
    "CollectSignAll": ("skulltula", "MapIconCollectSkullSign_00", "bool64"),
    "CollectHeart": ("heart", "MapIconCollectHeartPiece_00", None),
    "CollectHeartAll": ("heart", "MapIconCollectHeartPiece_00", None),
    "Facility": ("place", None, None),
    "EntranceAnchor": ("exit", None, None),
}


def language_prefix(language_txt: str) -> str:
    for line in language_txt.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return LANGUAGES.get(line, "USen")
    return "USen"


def location_names(z: ZsReader, prefix: str) -> dict[str, str]:
    mals = read_sarc(z.read(f"Mals/{prefix}.Product.110.sarc.zs"))
    return read_msbt(mals["LocationMsg/Location.msbt"])


def _objects(items_by_kind: dict, banc: str, floor: int | None, cam: dict, names: dict[str, str]) -> list[dict]:
    out, seen = [], set()
    for kind, (typ, icon, flag) in KINDS.items():
        for e in items_by_kind.get(kind, []) or []:
            oid = str(e["InstanceID"])
            if oid in seen or (kind == "EntranceAnchor" and not e.get("IsVisible", True)):
                continue
            seen.add(oid)
            px, py = project(e["Trans"][0], e["Trans"][2], cam)
            if not (0 <= px < IMAGE_W and 0 <= py < IMAGE_H):
                continue
            obj = {"id": oid, "type": typ, "map": banc, "floor": floor, "px": round(px, 1), "py": round(py, 1),
                   "icon": icon, "label": "", "flag": flag}
            if kind == "Facility":
                obj["icon"] = PLACE_ICONS.get(e["IconType"], PLACE_DEFAULT)
            elif kind == "EntranceAnchor":
                obj["icon"] = "MapIconDoor_01" if e.get("IconType") == 1 else "MapIconArrow_00"
                obj["rotate"] = e.get("IconRotate", 0)
                obj["label"] = names.get(e.get("Location", ""), e.get("Location", ""))
            out.append(obj)
    return out


def build_world(z: ZsReader, prefix: str, dungeon_textures: list[str], field_textures: set[str]) -> dict:
    """The world model (see the plan's Task 4 schema). Images are written separately by assets.write_maps."""
    mp = parse_byml(z.read("Banc/BancBasedResource/MapParam.byml.zs"))
    caps = parse_byml(z.read("Game/MapCaptureInfo/MapCaptureInfo.game__MapCaptureInfo.bgyml"))["MapCaptureParamArray"]
    menu = parse_byml(z.read("Game/MapMenuInfo/MapMenuInfo.game__ui__MapMenuInfo.bgyml"))["MapMenuParamArray"]
    names = location_names(z, prefix)
    zones, banc_to_zone = [], {}
    for i, entry in enumerate(menu[:MENU_ZONES]):
        zid = entry["LocationName"]
        c = caps[i]
        cam = {"x": c["CameraPos"]["X"], "z": c["CameraPos"]["Z"], "height": c["Height"]}
        dungeon = bool(c.get("IsDungeon"))
        zone = {"id": zid, "name": names.get(zid) or zid, "kind": "dungeon" if dungeon else "field",
                "maps": {}, "floors": [], "camera": cam, "objects": []}
        if dungeon:
            param = mp[zid]
            zone["maps"][zid] = {"age": "all", "image": None}
            for k, (floor, fname) in enumerate(zip(param["Floor"], floor_names(param["MinFloor"], param["FloorNum"]))):
                zone["floors"].append({"name": fname, "transY": floor["TransY"], "image": f"maps/{zid}_{fname}.webp"})
                zone["objects"] += _objects(floor, zid, k, cam, names)
            zone["maps"][zid]["image"] = zone["floors"][0]["image"] if zone["floors"] else None
            banc_to_zone[zid] = zid
        else:
            bancs = list(zip(entry["BancName"], ("child", "adult"), entry["TextureName"]))
            bancs += [(alt["BancName"], "adult", entry["TextureName"][1]) for alt in entry.get("ChangeBancInfo", [])]
            for banc, age, tex in bancs:
                if not tex or tex not in field_textures or banc in zone["maps"]:
                    continue  # e.g. no child map of Gerudo Fortress
                zone["maps"][banc] = {"age": age, "image": f"maps/{tex}.webp"}
                banc_to_zone.setdefault(banc, zid)
                zone["objects"] += _objects(mp.get(banc, {}), banc, None, cam, names)
        zones.append(zone)
    return {"zones": zones, "bancToZone": banc_to_zone, "image": {"width": IMAGE_W, "height": IMAGE_H}}
