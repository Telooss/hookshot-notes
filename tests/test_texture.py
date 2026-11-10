import os

import numpy as np
import pytest

from hookshot_notes.formats import font, nso, texture
from hookshot_notes.formats.bntx import list_textures
from hookshot_notes.formats.zs import ZsReader

KEY = bytes.fromhex("a6018502")


def test_swizzle_roundtrip():
    bw, bh, bpb, bhl = 13, 9, 16, 2
    data = os.urandom(bw * bh * bpb)
    size = texture.swizzled_size(bw, bh, bpb, bhl)
    raw = texture.swizzle(data, bw, bh, bpb, bhl, size)
    assert len(raw) == size
    assert texture.deswizzle(raw, bw, bh, bpb, bhl) == data


def test_swizzle_moves_bytes():
    # Tegra puts byte (x=16, y=0) at GOB offset 32; the Switch 2 swaps address bits 5 and 6, so it lands at 64
    data = bytes(range(64)) + bytes(64)
    raw = texture.swizzle(data, 4, 2, 16, 0, texture.swizzled_size(4, 2, 16, 0))
    assert raw[64] == 16 and raw[32] == 0


def test_font_decrypt():
    plain = b"OTTO" + bytes(range(60))
    enc = b"\x01\x02\x03\x04\x05\x06\x07\x08" + bytes(c ^ KEY[i % 4] for i, c in enumerate(plain))
    assert font.decrypt(enc) == plain


def test_build_id(tmp_path):
    main = tmp_path / "main"
    main.write_bytes(b"NSO0" + bytes(0x3C) + bytes(range(20)) + bytes(16))
    assert nso.build_id(main) == bytes(range(20)).hex()


@pytest.mark.game
def test_field_map_decodes(game_dir):
    buf = ZsReader(game_dir.romfs).read("UI/CustomTex/Map/Field/KokiriForest_Child_00.bntx.zs")
    info = list_textures(buf)["KokiriForest_Child_00"]
    im = texture.decode(buf, info)
    assert im.size == (2000, 1440)
    assert (np.asarray(im)[:, :, 3] > 0).mean() >= 0.30


@pytest.mark.game
def test_real_build_id(game_dir):
    assert nso.build_id(game_dir.exefs_main) == "e0f3ccfaf50065ae4ea01eb5aeb13b1a45da3348"
