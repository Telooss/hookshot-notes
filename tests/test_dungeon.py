import numpy as np
import pytest
from PIL import Image

from hookshot_notes.extract.dungeon import compose_floor, floor_for_height, floor_layers, floor_names
from hookshot_notes.extract.projection import project


def test_project_uses_width_over_height_field():
    cam = {"x": -5.0, "z": -12.0, "height": 400.0}
    assert project(-5.0, -12.0, cam) == (1000.0, 720.0)
    assert project(95.0, 38.0, cam) == (1500.0, 970.0)  # 100 units = 2000/400 * 100 px


def test_floor_names_skip_zero():
    assert floor_names(-2, 5) == ["B2", "B1", "1F", "2F", "3F"]
    assert floor_names(0, 2) == ["1F", "2F"]


def test_floor_for_height():
    floors = [{"transY": 0.0}, {"transY": 10.0}, {"transY": 20.0}]
    assert floor_for_height(floors, 15) == 1
    assert floor_for_height(floors, -5) == 0
    assert floor_for_height(floors, 99) == 2


def test_floor_layers_groups_by_floor_and_role():
    names = ["Deku_All", "Deku_1F_Back", "Deku_1F_State00_Main", "Deku_1F_State01_Main", "Deku_B1_Main", "Other_1F_Main"]
    assert floor_layers(names, "Deku") == {
        "1F": {"Back": "Deku_1F_Back", "State00_Main": "Deku_1F_State00_Main", "State01_Main": "Deku_1F_State01_Main"},
        "B1": {"Main": "Deku_B1_Main"},
    }


def test_compose_floor_puts_main_over_back_and_picks_state():
    size = (2000, 1440)
    back = Image.new("RGBA", size, (10, 10, 10, 255))
    s0 = Image.new("RGBA", size, (0, 0, 0, 0)); s0.putpixel((1, 1), (200, 0, 0, 255))
    s1 = Image.new("RGBA", size, (0, 0, 0, 0)); s1.putpixel((1, 1), (0, 200, 0, 255))
    layers = {"Back": back, "State00_Main": s0, "State01_Main": s1}
    assert compose_floor(layers, None).getpixel((1, 1)) == (200, 0, 0, 255)  # default: first state
    assert compose_floor(layers, "State01").getpixel((1, 1)) == (0, 200, 0, 255)
    assert compose_floor(layers, None).getpixel((0, 0)) == (10, 10, 10, 255)


def test_compose_floor_scales_half_resolution_layers():
    back = Image.new("RGBA", (1000, 720), (10, 10, 10, 255))
    main = Image.new("RGBA", (2000, 1440), (0, 0, 0, 0)); main.putpixel((1999, 1439), (200, 0, 0, 255))
    out = compose_floor({"Back": back, "Main": main}, None)
    assert out.size == (2000, 1440)
    assert out.getpixel((1999, 1439)) == (200, 0, 0, 255)
    assert out.getpixel((1500, 1000)) == (10, 10, 10, 255)


def _game(game_dir):
    from hookshot_notes.formats.byml import parse_byml
    from hookshot_notes.formats.zs import ZsReader
    z = ZsReader(game_dir.romfs)
    mp = parse_byml(z.read("Banc/BancBasedResource/MapParam.byml.zs"))
    cap = parse_byml(z.read("Game/MapCaptureInfo/MapCaptureInfo.game__MapCaptureInfo.bgyml"))["MapCaptureParamArray"]
    menu = parse_byml(z.read("Game/MapMenuInfo/MapMenuInfo.game__ui__MapMenuInfo.bgyml"))["MapMenuParamArray"]
    return z, mp, cap, menu


def _image(z, path):
    from hookshot_notes.formats.bntx import list_textures
    from hookshot_notes.formats.texture import decode
    buf = z.read(path)
    return decode(buf, next(iter(list_textures(buf).values())))


def _cam(c):
    return {"x": c["CameraPos"]["X"], "z": c["CameraPos"]["Z"], "height": c["Height"]}


@pytest.mark.game
def test_dungeon_objects_on_floor(game_dir):
    z, mp, cap, menu = _game(game_dir)
    names = [p.name[:-len(".bntx.zs")] for p in (game_dir.romfs / "UI/CustomTex/Map/Dungeon").iterdir()]
    hit = total = 0
    for i in range(20, 30):
        dungeon = menu[i]["LocationName"]
        param, cam = mp[dungeon], _cam(cap[i])
        layers = floor_layers(names, dungeon)
        for floor, fname in zip(param["Floor"], floor_names(param["MinFloor"], param["FloorNum"])):
            imgs = {role: _image(z, f"UI/CustomTex/Map/Dungeon/{n}.bntx.zs") for role, n in layers[fname].items()}
            alpha = np.asarray(compose_floor(imgs, None))[:, :, 3]
            for e in floor.get("TBox", []) + floor.get("CollectSign", []):
                px, py = project(e["Trans"][0], e["Trans"][2], cam)
                total += 1
                hit += 0 <= px < 2000 and 0 <= py < 1440 and alpha[int(py), int(px)] > 0
    assert hit / total >= 0.90, (hit, total)


@pytest.mark.game
def test_field_objects_on_map(game_dir):
    z, mp, cap, menu = _game(game_dir)
    hit = total = 0
    for i in range(20):
        cam = _cam(cap[i])
        for banc, tex in zip(menu[i]["BancName"], menu[i]["TextureName"]):
            if banc not in mp or not tex:
                continue
            alpha = np.asarray(_image(z, f"UI/CustomTex/Map/Field/{tex}.bntx.zs"))[:, :, 3]
            for key, items in mp[banc].items():
                if key in ("Floor", "EntranceAnchor") or not isinstance(items, list):
                    continue
                for e in items:
                    px, py = project(e["Trans"][0], e["Trans"][2], cam)
                    total += 1
                    hit += 0 <= px < 2000 and 0 <= py < 1440 and alpha[int(py), int(px)] > 0
    assert hit / total >= 0.90, (hit, total)
