"""progress.sav reader (format notes: docs/notes/sauvegarde.md)."""
from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

from .gamedata import flag_hash

MAGIC = 0x01020304
SAVE_TYPE_HASH = 2749067540  # GameDataList MetaData SaveTypeHash of progress.sav; its pair points at the Bool64bitKey keys
LIFE, MAX_LIFE = flag_hash("PlayerStatus.Life"), flag_hash("PlayerStatus.MaxLife")


@dataclass(frozen=True)
class SaveState:
    collected: frozenset[int]
    life: int
    max_life: int
    mtime: float


def find_latest_save(saves: Path) -> Path | None:
    found = list(Path(saves).glob("*/slot_*/progress.sav")) if Path(saves).is_dir() else []
    return max(found, key=lambda p: p.stat().st_mtime, default=None)


def parse_save(buf: bytes, mtime: float = 0.0) -> SaveState:
    magic, _, table_end = struct.unpack_from("<III", buf, 0)
    if magic != MAGIC or not 0x28 < table_end <= len(buf):
        raise ValueError("not a progress.sav")
    values, keys_at = {}, None
    for o in range(0x28, table_end, 8):
        h, v = struct.unpack_from("<II", buf, o)
        if h == SAVE_TYPE_HASH:
            keys_at = v
        elif h:
            values[h] = v
    if keys_at is None:
        raise ValueError("no Bool64bitKey section")
    keys, o = [], keys_at
    while True:
        k = struct.unpack_from("<Q", buf, o)[0]  # raises at end of buffer: a truncated file has no terminator
        if k == 0:
            break
        keys.append(k)
        o += 8
    life = struct.unpack("<i", struct.pack("<I", values.get(LIFE, 0)))[0]
    max_life = struct.unpack("<i", struct.pack("<I", values.get(MAX_LIFE, 0)))[0]
    return SaveState(frozenset(keys), life, max_life, mtime)


class SaveReader:
    """Keeps the last valid state, so a save caught mid-write never un-ticks everything."""

    def __init__(self):
        self.last: SaveState | None = None

    def read(self, path: Path | None) -> SaveState | None:
        try:
            p = Path(path)
            self.last = parse_save(p.read_bytes(), p.stat().st_mtime)
        except (OSError, ValueError, struct.error, TypeError):
            pass
        return self.last
