import json
import shutil

import pytest

from hookshot_notes.extract import run
from hookshot_notes.formats.msbt import read_msbt
from hookshot_notes.paths import GameDir
from tests.builders import build_msbt

TAG = b"\x0e" + bytes.fromhex("0000 0300 0400") + b"\x01\x02\x03\x04"  # group 0, type 3, 4 bytes of params


def test_msbt_reads_labels_and_skips_tags():
    data = build_msbt({"KokiriForest": "Forêt Kokiri".encode(), "ForestTemple": TAG + "Temple de la Forêt".encode()})
    assert read_msbt(data) == {"KokiriForest": "Forêt Kokiri", "ForestTemple": "Temple de la Forêt"}


def test_extract_is_atomic(tmp_path):
    game = tmp_path / "Hookshot"
    (game / "romfs").mkdir(parents=True)
    (game / ".hookshot_exefs").mkdir()
    out = tmp_path / "hookshot-notes-data"
    with pytest.raises(Exception):
        run.extract(GameDir(game), out, lambda step, frac: None)
    assert not out.exists()
    assert not out.with_name(out.name + ".tmp").exists()


@pytest.fixture(scope="module")
def extracted(game_dir, tmp_path_factory):
    out = tmp_path_factory.mktemp("cache") / "hookshot-notes-data"
    run.extract(game_dir, out, lambda step, frac: None)
    yield out
    shutil.rmtree(out, ignore_errors=True)


@pytest.mark.game
def test_world_contents(game_dir, extracted):
    from hookshot_notes.formats.nso import build_id
    world = json.loads((extracted / "world.json").read_text("utf-8"))
    assert len(world["zones"]) >= 30
    assert world["bancToZone"]["KokiriForest_Child"] == "KokiriForest"
    kokiri = next(z for z in world["zones"] if z["id"] == "KokiriForest")
    assert kokiri["name"] == "Forêt Kokiri"  # language.txt = fr
    skulls = [o for o in kokiri["objects"] if o["type"] == "skulltula" and o["map"] == "KokiriForest_Child"]
    assert len(skulls) == 3 and all(o["flag"] == "bool64" and isinstance(o["id"], str) for o in skulls)
    for zone in world["zones"]:
        for o in zone["objects"]:
            assert 0 <= o["px"] < 2000 and 0 <= o["py"] < 1440, (zone["id"], o)
        images = [m["image"] for m in zone["maps"].values()] + [f["image"] for f in zone["floors"]]
        assert images and all((extracted / im).is_file() for im in images), zone["id"]
    deku = next(z for z in world["zones"] if z["id"] == "InsideTheDekuTree")
    assert [f["name"] for f in deku["floors"]] == ["B2", "B1", "1F", "2F", "3F"]
    assert (extracted / "icons" / "MapIconCollectSkullSign_00.png").is_file()
    assert (extracted / "fonts" / "cetra.otf").read_bytes()[:4] == b"OTTO"
    assert run.cache_is_valid(extracted, build_id(game_dir.exefs_main))
    assert not run.cache_is_valid(extracted, "0" * 40)


def test_swap_in_keeps_player_files(tmp_path):
    out, tmp = tmp_path / "hookshot-notes-data", tmp_path / "hookshot-notes-data.tmp"
    out.mkdir(); tmp.mkdir()
    (out / "visited.json").write_text('["KokiriForest"]', "utf-8")
    (out / "state.json").write_text('{"zone": "KokiriForest"}', "utf-8")
    (out / "world.json").write_text("old", "utf-8")
    (tmp / "world.json").write_text("new", "utf-8")
    run.swap_in(tmp, out)
    assert (out / "world.json").read_text("utf-8") == "new"
    assert (out / "visited.json").read_text("utf-8") == '["KokiriForest"]'
    assert (out / "state.json").exists() and not tmp.exists()
    assert not out.with_name(out.name + ".old").exists()


@pytest.mark.game
def test_adult_castle_uses_its_own_camera(extracted):
    world = json.loads((extracted / "world.json").read_text("utf-8"))
    castle = next(z for z in world["zones"] if z["id"] == "HyruleCastle")
    ganon = castle["maps"]["GanonCastle"]
    assert ganon["camera"] != castle["maps"]["HyruleCastle"]["camera"]
    assert len([o for o in castle["objects"] if o["map"] == "GanonCastle"]) >= 4
