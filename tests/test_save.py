import os
import struct
import time

import pytest

from hookshot_notes.game.gamedata import flag_hash
from hookshot_notes.game.save import SAVE_TYPE_HASH, SaveReader, find_latest_save


def build_save(life: int, max_life: int, keys: list[int]) -> bytes:
    pairs = [(0, 2), (flag_hash("PlayerStatus.Life"), life), (flag_hash("PlayerStatus.MaxLife"), max_life), (0, 28)]
    table_end = 0x28 + 8 * (len(pairs) + 1)
    pairs.append((SAVE_TYPE_HASH, table_end))
    head = struct.pack("<III", 0x01020304, 0x2D80EB, table_end) + bytes(0x28 - 12)
    body = b"".join(struct.pack("<II", h, v) for h, v in pairs)
    return head + body + b"".join(struct.pack("<Q", k) for k in sorted(keys)) + bytes(8)


def test_flag_hash_known_values():
    assert flag_hash("PlayerStatus.Life") == 833312128
    assert flag_hash("PlayerStatus.SavePos") == 3364127117


def test_reads_life_and_collected_keys(tmp_path):
    p = tmp_path / "progress.sav"
    p.write_bytes(build_save(12, 16, [2**63 + 5, 7]))
    state = SaveReader().read(p)
    assert (state.life, state.max_life) == (12, 16)
    assert state.collected == frozenset({7, 2**63 + 5})


def test_find_latest_save(tmp_path):
    paths = []
    for i, slot in enumerate(["a/slot_00", "a/slot_01", "b/slot_00"]):
        p = tmp_path / slot / "progress.sav"
        p.parent.mkdir(parents=True)
        p.write_bytes(b"x")
        os.utime(p, (time.time() - 100 + i * 10,) * 2)
        paths.append(p)
    os.utime(paths[1], (time.time() + 5,) * 2)
    assert find_latest_save(tmp_path) == paths[1]
    assert find_latest_save(tmp_path / "missing") is None


def test_truncated_save_keeps_previous(tmp_path):
    p = tmp_path / "progress.sav"
    reader = SaveReader()
    p.write_bytes(build_save(12, 16, [7]))
    good = reader.read(p)
    p.write_bytes(build_save(12, 16, [7])[:10])
    assert reader.read(p) == good
    assert SaveReader().read(p) is None


@pytest.mark.game
def test_real_save_life(game_dir):
    state = SaveReader().read(find_latest_save(game_dir.saves))
    assert state.life > 0 and state.max_life >= state.life
