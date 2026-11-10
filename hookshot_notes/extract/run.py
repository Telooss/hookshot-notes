"""First-run extraction into hookshot-notes-data/ (all or nothing)."""
import json
import shutil
from collections.abc import Callable
from pathlib import Path

from ..formats.nso import build_id
from ..formats.zs import ZsReader
from ..paths import GameDir
from . import assets
from .world import build_world, language_prefix

FORMAT = 1


def extract(game: GameDir, out: Path, progress: Callable[[str, float], None]) -> None:
    tmp = out.with_name(out.name + ".tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    try:
        tmp.mkdir(parents=True)
        bid = build_id(game.exefs_main)
        z = ZsReader(game.romfs)
        lang = game.language_file.read_text("utf-8") if game.language_file.is_file() else ""
        maps = game.romfs / "UI/CustomTex/Map"
        dungeon_textures = [p.name[:-len(".bntx.zs")] for p in (maps / "Dungeon").iterdir()]
        field_textures = {p.name[:-len(".bntx.zs")] for p in (maps / "Field").iterdir()}
        progress("monde", 0.0)
        world = build_world(z, language_prefix(lang), dungeon_textures, field_textures)
        assets.write_maps(z, world, tmp, dungeon_textures, progress)
        progress("icônes", 0.9)
        assets.write_icons(z, tmp)
        assets.write_fonts(z, tmp)
        (tmp / "world.json").write_text(json.dumps(world, ensure_ascii=False), "utf-8")
        (tmp / "meta.json").write_text(json.dumps({"build_id": bid, "format": FORMAT}), "utf-8")
        shutil.rmtree(out, ignore_errors=True)
        tmp.rename(out)
        progress("terminé", 1.0)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise


def cache_is_valid(out: Path, build_id: str) -> bool:
    try:
        meta = json.loads((out / "meta.json").read_text("utf-8"))
    except (OSError, ValueError):
        return False
    return meta.get("build_id") == build_id and meta.get("format") == FORMAT and (out / "world.json").is_file()
