"""Images and fonts of the local cache, decoded from the player's romfs."""
from collections.abc import Callable
from pathlib import Path

from ..formats import font
from ..formats.bntx import list_textures
from ..formats.texture import decode
from ..formats.zs import ZsReader
from .dungeon import compose_floor, floor_layers

COMMON = "UI/Layout2Archive/Common.Product.100.Nin_Ounce_NVN2.bntx.zs"
UI_TEXTURES = ("MapLocationNameBgFill_00", "MapLocationNameBgOutline_00", "LocationDecoLine_00")
FONTS = {"cetra.otf": "Font2/Scalable/CetraDisplayPro-Medium.Nin_Ounce_NVN2.bfotf.zs",
         "clarimo.otf": "Font2/Scalable/ClarimoUDPE-DemiBold.Nin_Ounce_NVN2.bfotf.zs"}


def _single(z: ZsReader, rel: str):
    buf = z.read(rel)
    return decode(buf, next(iter(list_textures(buf).values())))


def write_maps(z: ZsReader, world: dict, out: Path, dungeon_textures: list[str],
               progress: Callable[[str, float], None]) -> None:
    jobs = []
    for zone in world["zones"]:
        if zone["kind"] == "field":
            jobs += [("field", m["image"]) for m in zone["maps"].values()]
        else:
            layers = floor_layers(dungeon_textures, zone["id"])
            jobs += [("dungeon", f["image"], layers.get(f["name"], {})) for f in zone["floors"]]
    (out / "maps").mkdir(parents=True, exist_ok=True)
    for n, job in enumerate(jobs):
        target = out / job[1]
        progress("cartes", n / len(jobs))
        if target.exists():
            continue
        if job[0] == "field":
            im = _single(z, f"UI/CustomTex/Map/Field/{Path(job[1]).stem}.bntx.zs")
        else:
            if not job[2]:
                raise ValueError(f"no layers for {job[1]}")
            im = compose_floor({role: _single(z, f"UI/CustomTex/Map/Dungeon/{name}.bntx.zs")
                                for role, name in job[2].items() if role.endswith("Main") or role == "Back"}, None)
        im.save(target, "WEBP", quality=85)


def write_icons(z: ZsReader, out: Path) -> None:
    buf = z.read(COMMON)
    textures = list_textures(buf)
    (out / "icons").mkdir(parents=True, exist_ok=True)
    (out / "ui").mkdir(parents=True, exist_ok=True)
    for name, info in textures.items():
        if name.startswith("MapIcon"):
            decode(buf, info).save(out / "icons" / f"{name}.png")
        elif name in UI_TEXTURES:
            decode(buf, info).save(out / "ui" / f"{name}.png")


def write_fonts(z: ZsReader, out: Path) -> None:
    (out / "fonts").mkdir(parents=True, exist_ok=True)
    for target, rel in FONTS.items():
        (out / "fonts" / target).write_bytes(font.decrypt(z.read(rel)))
