"""Combines the live position, the save file and the tool's own memory into one snapshot for the pages."""
from __future__ import annotations

import json
import math
import queue
import threading
import time
from pathlib import Path

from ..extract.dungeon import floor_for_height
from ..extract.projection import project
from ..game.live import LiveState
from ..game.save import SaveReader, SaveState, find_latest_save


class StateHub:
    def __init__(self, world: dict, data_dir: Path):
        self.world, self.data_dir = world, Path(data_dir)
        self.zones = {z["id"]: z for z in world["zones"]}
        self.readable = {o["id"] for z in world["zones"] for o in z["objects"] if o["flag"] == "bool64"}
        self.known = {o["id"] for z in world["zones"] for o in z["objects"]}
        self.visited = set(self._load_visited())
        self.zone = self.banc = None
        self._snap = self._build("no_game", None, None, None)
        self._subs: list[queue.Queue] = []
        self._lock = threading.Lock()

    def _load_visited(self) -> list[str]:
        try:
            return [z for z in json.loads((self.data_dir / "visited.json").read_text("utf-8")) if z in self.zones]
        except (OSError, ValueError):
            return []

    def _build(self, status: str, floor: int | None, player: dict | None, save: SaveState | None) -> dict:
        collected = sorted(str(k) for k in (save.collected if save else ()) if str(k) in self.known)
        got = sum(1 for k in collected if k in self.readable)
        return {"status": status, "zone": self.zone, "banc": self.banc, "floor": floor, "player": player,
                "collected": collected, "visited": sorted(self.visited),
                "percent": round(100.0 * got / len(self.readable), 1) if self.readable else 0.0}

    def update(self, live: LiveState | None, status: str, save: SaveState | None) -> dict | None:
        floor = self._snap["floor"]
        player = None
        if live is not None and live.banc in self.world["bancToZone"]:
            self.banc, self.zone = live.banc, self.world["bancToZone"][live.banc]
            zone = self.zones[self.zone]
            px, py = project(live.x, live.z, zone["camera"])
            player = {"px": round(px, 1), "py": round(py, 1)}
            floor = floor_for_height(zone["floors"], live.y) if zone["floors"] else None
            if self.zone not in self.visited:
                self.visited.add(self.zone)
                self._save_visited()
        snap = self._build(status, floor, player, save)
        with self._lock:
            if snap == self._snap:
                return None
            self._snap = snap
            data = json.dumps(snap, ensure_ascii=False)
            for q in self._subs:
                q.put(data)
        return snap

    def _save_visited(self) -> None:
        try:
            (self.data_dir / "visited.json").write_text(json.dumps(sorted(self.visited)), "utf-8")
        except OSError:
            pass  # the map keeps working; zones are remembered again next time

    def snapshot(self) -> dict:
        return self._snap

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue()
        with self._lock:
            q.put(json.dumps(self._snap, ensure_ascii=False))
            self._subs.append(q)
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        with self._lock:
            if q in self._subs:
                self._subs.remove(q)


def poll_forever(hub: StateHub, source, saves_dir: Path | None, stop: threading.Event, interval: float = 0.25) -> None:
    """Background loop: live source (Tracker or DemoSource) + latest save, re-read only when it changes."""
    reader, seen, save = SaveReader(), None, None
    while not stop.is_set():
        path = find_latest_save(saves_dir) if saves_dir else None
        try:
            stamp = (path, path.stat().st_mtime) if path else None
        except OSError:
            stamp = seen
        if stamp != seen:
            seen, save = stamp, reader.read(path)
        hub.update(source.poll(), source.status, save)
        stop.wait(interval)


class DemoSource:
    """Fake Link walking in a circle in one zone, to try the page without the game."""

    def __init__(self, world: dict, banc: str):
        zone = next(z for z in world["zones"] if world["bancToZone"].get(banc) == z["id"])
        self.banc, self.cam, self.status = banc, zone["camera"], "live"
        self.y = zone["floors"][0]["transY"] + 1 if zone["floors"] else 100.0

    def poll(self) -> LiveState:
        a = time.time() * 2 * math.pi / 20
        r = self.cam["height"] / 6
        return LiveState(self.banc, self.cam["x"] + r * math.cos(a), self.y, self.cam["z"] + r * math.sin(a), time.time())
