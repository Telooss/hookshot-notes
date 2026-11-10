from __future__ import annotations

from pathlib import Path

import zstandard

from .sarc import read_sarc

DICT_PACK = "Pack/ZsDic.pack.zs"


class ZsReader:
    """Reads romfs files; `.zs` files are zstd frames, with a dictionary chosen by the frame's dictionary ID."""

    def __init__(self, romfs: Path, dicts: dict[str, bytes] | None = None):
        self.romfs = Path(romfs)
        if dicts is None:
            pack = zstandard.ZstdDecompressor().decompress((self.romfs / DICT_PACK).read_bytes())
            dicts = read_sarc(pack)
        self._by_id = {}
        for raw in dicts.values():
            d = zstandard.ZstdCompressionDict(raw)
            self._by_id[d.dict_id()] = d

    @classmethod
    def from_dicts(cls, romfs: Path, dicts: dict[str, bytes]) -> ZsReader:
        return cls(romfs, dicts)

    def read(self, rel: str) -> bytes:
        raw = (self.romfs / rel).read_bytes()
        if not rel.endswith(".zs"):
            return raw
        did = zstandard.get_frame_parameters(raw).dict_id
        d = self._by_id.get(did) if did else None
        if did and d is None:
            raise ValueError(f"{rel}: unknown zstd dictionary {did}")
        return zstandard.ZstdDecompressor(dict_data=d).decompress(raw, max_output_size=1 << 31)
