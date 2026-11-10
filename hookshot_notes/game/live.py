"""Live 'current map + Link position' record in the game's GameData storage.

Layout at guest address A: [u64 pointer to A+12][u32 capacity 0x40][map name, 64 bytes][8 zero bytes][3 float x, y, z].
Updated about twice a second; same address across zone changes (checked in the feasibility study)."""
from __future__ import annotations

import math
import struct
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from .memory import Memory

HEAP_LO, HEAP_HI = 0x1000000000, 0x1200000000
CHUNK = 64 << 20
CAP = b"\x40\x00\x00\x00"
NAME_AT, POS_AT = 12, 84  # offsets from the record start
SEARCH_MIN, SEARCH_MAX = 5.0, 60.0  # back-off between two full memory searches that found nothing


@dataclass(frozen=True)
class LiveState:
    banc: str
    x: float
    y: float
    z: float
    t: float


def _record_at(chunk: bytes, i: int, guest: int) -> tuple[str, tuple[float, float, float]] | None:
    """Parse a record whose capacity field is at chunk[i] (guest address `guest` of that field)."""
    if i < 8 or i + 4 + 64 + 8 + 12 > len(chunk):
        return None
    if struct.unpack_from("<Q", chunk, i - 8)[0] != guest + 4 or chunk[i + 68:i + 76] != bytes(8):
        return None
    try:
        name = chunk[i + 4:i + 68].split(b"\0")[0].decode("ascii")
    except UnicodeDecodeError:
        return None
    pos = struct.unpack_from("<3f", chunk, i + 76)
    if not name or not all(math.isfinite(v) and abs(v) < 5000 for v in pos):
        return None
    return name, pos


def find_record(mem: Memory, banc_names: set[str]) -> int | None:
    """Guest address of the position (x, y, z) of the live record, or None."""
    found = []
    for base, size in mem.regions(HEAP_LO, HEAP_HI):
        off = 0
        while off < size:
            n = min(CHUNK, size - off)
            chunk = mem.read(base + off, min(n + 96, size - off)) or b""  # overlap: records across chunk edges
            i = chunk.find(CAP)
            while 0 <= i < n:
                rec = _record_at(chunk, i, base + off + i)
                if rec and rec[0] in banc_names:
                    found.append((base + off + i - 8 + POS_AT, rec[1]))
                i = chunk.find(CAP, i + 4)
            off += n
    live = [a for a, pos in found if pos != (0.0, 0.0, 0.0)]  # a record still at the origin is not Link yet
    return live[0] if live else None


class Tracker:
    def __init__(self, open_memory: Callable[[], Memory | None], banc_names: set[str]):
        self.open_memory, self.banc_names = open_memory, banc_names
        self.mem: Memory | None = None
        self.addr: int | None = None
        self.next_search = 0.0
        self.search_delay = SEARCH_MIN
        self.status: Literal["no_game", "searching", "live"] = "no_game"

    def _lost(self) -> None:
        self.mem, self.addr, self.status = None, None, "no_game"
        self.search_delay, self.next_search = SEARCH_MIN, 0.0

    def poll(self) -> LiveState | None:
        if self.mem is None:
            self.mem = self.open_memory()
            if self.mem is None:
                self._lost()
                return None
        if self.addr is None:
            if self.status != "searching":  # publish "searching" before the (long) scan blocks this loop
                self.status = "searching"
                return None
            if time.monotonic() < self.next_search:
                return None
            self.addr = find_record(self.mem, self.banc_names)
            if self.addr is None:
                if self.next_search:  # second failure in a row or later: wait twice as long
                    self.search_delay = min(self.search_delay * 2, SEARCH_MAX)
                self.next_search = time.monotonic() + self.search_delay
                return None
            self.search_delay, self.next_search = SEARCH_MIN, 0.0
        start = self.addr - POS_AT
        head = self.mem.read(start, POS_AT + 12)
        if head is None:
            self._lost()
            return None
        rec = _record_at(head, 8, start + 8)
        if rec is None:  # the record moved or was freed: search again
            self.addr = None
            return None
        self.status = "live"
        name, (x, y, z) = rec
        return LiveState(name, x, y, z, time.time())


if __name__ == "__main__":  # manual check with the game running: python -m hookshot_notes.game.live <romfs-dir>
    import sys
    from ..formats.byml import parse_byml
    from ..formats.zs import ZsReader
    from .memory import open_game_memory
    bancs = set(parse_byml(ZsReader(sys.argv[1]).read("Banc/BancBasedResource/MapParam.byml.zs")))
    tracker = Tracker(open_game_memory, bancs)
    while True:
        t0 = time.time()
        state = tracker.poll()
        print(tracker.status, state, f"({time.time() - t0:.1f}s)", flush=True)
        time.sleep(0.5)
