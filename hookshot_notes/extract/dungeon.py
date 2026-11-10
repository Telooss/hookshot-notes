"""Dungeon maps: one set of layers per floor (see docs/notes/donjons.md)."""
import re

from PIL import Image

from .projection import IMAGE_H, IMAGE_W

_FLOOR = re.compile(r"^(B\d+|\d+F)$")


def floor_names(min_floor: int, count: int) -> list[str]:
    """MapParam floor order: levels from MinFloor upward, with no level 0 (B2, B1, 1F, 2F...)."""
    levels = [lv for lv in range(min_floor, min_floor + count + 1) if lv != 0][:count]
    return [f"B{-lv}" if lv < 0 else f"{lv}F" for lv in levels]


def floor_layers(romfs_names: list[str], dungeon: str) -> dict[str, dict[str, str]]:
    """floor -> role ("Main", "Back", "Grad", "Alpha", "State00_Main"...) -> texture name."""
    out: dict[str, dict[str, str]] = {}
    for name in romfs_names:
        if not name.startswith(dungeon + "_"):
            continue
        floor, _, role = name[len(dungeon) + 1:].partition("_")
        if _FLOOR.match(floor) and role:
            out.setdefault(floor, {})[role] = name
    return out


def main_layer(roles: list[str], state: str | None) -> str | None:
    """The floor drawing to show: "Main", or the requested "StateNN_Main", or the first state."""
    if "Main" in roles:
        return "Main"
    if state and f"{state}_Main" in roles:
        return f"{state}_Main"
    states = sorted(r for r in roles if r.endswith("_Main"))
    return states[0] if states else None


def compose_floor(layers: dict[str, Image.Image], state: str | None) -> Image.Image:
    """Back (darker floor background) with the floor drawing over it, at map size (some layers are
    stored at half resolution); Grad/Alpha are not used in v1."""
    def full(im: Image.Image) -> Image.Image:
        im = im.convert("RGBA")
        return im if im.size == (IMAGE_W, IMAGE_H) else im.resize((IMAGE_W, IMAGE_H), Image.BILINEAR)
    out = full(layers["Back"]) if "Back" in layers else Image.new("RGBA", (IMAGE_W, IMAGE_H), (0, 0, 0, 0))
    main = main_layer(list(layers), state)
    if main:
        out.alpha_composite(full(layers[main]))
    return out


def floor_for_height(floors: list[dict], y: float) -> int:
    """Index of the highest floor whose transY is at or below y (the lowest floor if y is below all)."""
    below = [i for i, f in enumerate(floors) if f["transY"] <= y]
    if below:
        return max(below, key=lambda i: floors[i]["transY"])
    return min(range(len(floors)), key=lambda i: floors[i]["transY"])
