import struct

from hookshot_notes.game.live import Tracker, find_record

HEAP = 0x1000000000
BANCS = {"KokiriForest_Child", "HyruleField_Child"}


def record(at: int, name: str, pos, cap: int = 0x40) -> bytes:
    """GameData string record at guest address `at`: [u64 ptr to text][u32 cap][text 64][8 zero][3 floats]."""
    return struct.pack("<QI", at + 12, cap) + name.encode().ljust(64, b"\0") + bytes(8) + struct.pack("<3f", *pos)


class FakeMemory:
    def __init__(self, size=0x4000):
        self.base, self.buf = HEAP, bytearray(size)

    def put(self, guest: int, data: bytes):
        self.buf[guest - self.base:guest - self.base + len(data)] = data

    def read(self, guest, n):
        o = guest - self.base
        return bytes(self.buf[o:o + n]) if 0 <= o and o + n <= len(self.buf) else None

    def regions(self, lo, hi):
        yield self.base, len(self.buf)


def test_find_record_pattern():
    mem = FakeMemory()
    mem.put(HEAP + 0x100, record(HEAP + 0x100, "KokiriForest_Child", (0.0, 0.0, 0.0)))  # decoy at the origin
    mem.put(HEAP + 0x800, record(HEAP + 0x800, "KokiriForest_Child", (1.0, 2.0, 3.0)))
    assert find_record(mem, BANCS) == HEAP + 0x800 + 84


def test_rejects_wrong_capacity_and_unknown_name():
    mem = FakeMemory()
    mem.put(HEAP + 0x100, record(HEAP + 0x100, "KokiriForest_Child", (1.0, 2.0, 3.0), cap=0x20))
    mem.put(HEAP + 0x800, record(HEAP + 0x800, "Npc_Kokiri_011_Child", (1.0, 2.0, 3.0)))
    assert find_record(mem, BANCS) is None


def test_tracker_follows_zone_change():
    mem = FakeMemory()
    mem.put(HEAP + 0x800, record(HEAP + 0x800, "KokiriForest_Child", (1.0, 2.0, 3.0)))
    tracker = Tracker(lambda: mem, BANCS)
    tracker.poll()
    assert tracker.poll().banc == "KokiriForest_Child"
    mem.put(HEAP + 0x800, record(HEAP + 0x800, "HyruleField_Child", (5.0, 6.0, 7.0)))
    mem.regions = lambda lo, hi: iter(())  # a new search would find nothing
    state = tracker.poll()
    assert (state.banc, state.x, state.z) == ("HyruleField_Child", 5.0, 7.0)


def test_tracker_survives_process_exit():
    mems = [None]
    tracker = Tracker(lambda: mems[0], BANCS)
    assert tracker.poll() is None and tracker.status == "no_game"
    mem = FakeMemory()
    mem.put(HEAP + 0x1200, record(HEAP + 0x1200, "KokiriForest_Child", (9.0, 8.0, 7.0)))
    mems[0] = mem
    assert tracker.poll() is None and tracker.status == "searching"  # announced before the scan
    state = tracker.poll()
    assert tracker.status == "live" and (state.x, state.y, state.z) == (9.0, 8.0, 7.0)
    mem.read = lambda guest, n: None  # the process went away
    assert tracker.poll() is None and tracker.status == "no_game"


def test_zero_only_record_is_ignored():
    mem = FakeMemory()
    mem.put(HEAP + 0x100, record(HEAP + 0x100, "KokiriForest_Child", (0.0, 0.0, 0.0)))
    assert find_record(mem, BANCS) is None


def test_tracker_announces_search_before_scanning():
    mem = FakeMemory()
    mem.put(HEAP + 0x800, record(HEAP + 0x800, "KokiriForest_Child", (1.0, 2.0, 3.0)))
    scans = []
    regions = mem.regions
    mem.regions = lambda lo, hi: (scans.append(1), regions(lo, hi))[1]
    tracker = Tracker(lambda: mem, BANCS)
    assert tracker.poll() is None and tracker.status == "searching" and not scans
    assert tracker.poll().x == 1.0 and scans


def test_tracker_backs_off_between_failed_searches(monkeypatch):
    from hookshot_notes.game import live as live_mod
    clock = [1000.0]
    monkeypatch.setattr(live_mod.time, "monotonic", lambda: clock[0])
    mem = FakeMemory()  # nothing to find
    tracker = Tracker(lambda: mem, BANCS)
    delays = []
    for _ in range(7):
        tracker.poll()          # announce or scan
        tracker.poll()
        delays.append(tracker.search_delay)
        clock[0] += 1000
    assert delays[0] == 5 and delays[-1] == 60 and delays == sorted(delays)
