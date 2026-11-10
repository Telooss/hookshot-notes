import zstandard
import pytest

from hookshot_notes.formats.byml import parse_byml
from hookshot_notes.formats.sarc import read_sarc
from hookshot_notes.formats.zs import ZsReader
from tests.builders import build_byml, build_sarc


@pytest.mark.parametrize("big", [False, True])
def test_byml_little_and_big_endian(big):
    assert parse_byml(build_byml({"a": 1, "b": [True, "x"]}, big_endian=big)) == {"a": 1, "b": [True, "x"]}


def test_byml_hash32_dict():
    data = build_byml({"h": {0x11223344: 5, 0xAABBCCDD: 6}})
    assert parse_byml(data) == {"h": {0x11223344: 5, 0xAABBCCDD: 6}}


def test_sarc_roundtrip():
    assert read_sarc(build_sarc({"a/b.txt": b"hi", "c": b""})) == {"a/b.txt": b"hi", "c": b""}


def test_zs_picks_dictionary_by_id(tmp_path):
    samples = [f"actor {i} pos {i * 3} name Npc_{i % 7}".encode() * 4 for i in range(400)]
    trained = zstandard.train_dictionary(2048, samples)
    payload = b"actor 9 pos 27 name Npc_2" * 20
    (tmp_path / "with.bin.zs").write_bytes(zstandard.ZstdCompressor(dict_data=trained).compress(payload))
    (tmp_path / "plain.bin.zs").write_bytes(zstandard.ZstdCompressor().compress(payload))
    (tmp_path / "raw.bin").write_bytes(b"raw")
    reader = ZsReader.from_dicts(tmp_path, {"zs.zsdic": trained.as_bytes()})
    assert reader.read("with.bin.zs") == payload
    assert reader.read("plain.bin.zs") == payload
    assert reader.read("raw.bin") == b"raw"


@pytest.mark.game
def test_gamedatalist_shape(game_dir):
    data = parse_byml(ZsReader(game_dir.romfs).read("GameData/GameDataList.Product.110.byml.zs"))["Data"]
    assert "Bool64bitKey" in data and "Vector3" in data
