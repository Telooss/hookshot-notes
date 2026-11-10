import http.client
import json
import threading

from hookshot_notes.game.live import LiveState
from hookshot_notes.game.save import SaveState
from hookshot_notes.server import http as web
from hookshot_notes.server.state import StateHub

WORLD = {
    "zones": [
        {"id": "KokiriForest", "name": "Forêt Kokiri", "kind": "field", "floors": [],
         "maps": {"KokiriForest_Child": {"age": "child", "image": "maps/k.webp"}},
         "camera": {"x": 0.0, "z": 0.0, "height": 200.0},
         "objects": [
             {"id": "11", "type": "skulltula", "map": "KokiriForest_Child", "floor": None, "px": 1.0, "py": 1.0, "icon": "i", "label": "", "flag": "bool64"},
             {"id": "12", "type": "chest", "map": "KokiriForest_Child", "floor": None, "px": 2.0, "py": 2.0, "icon": "i", "label": "", "flag": "bool64"},
             {"id": "13", "type": "heart", "map": "KokiriForest_Child", "floor": None, "px": 3.0, "py": 3.0, "icon": "i", "label": "", "flag": None},
         ]},
        {"id": "Deku", "name": "Arbre Mojo", "kind": "dungeon", "maps": {"Deku": {"age": "all", "image": "maps/d0.webp"}},
         "floors": [{"name": "1F", "transY": 0.0, "image": "maps/d0.webp"}, {"name": "2F", "transY": 20.0, "image": "maps/d1.webp"}],
         "camera": {"x": 0.0, "z": 0.0, "height": 200.0}, "objects": []},
    ],
    "bancToZone": {"KokiriForest_Child": "KokiriForest", "Deku": "Deku"},
    "image": {"width": 2000, "height": 1440},
}


def live(banc, x=0.0, y=0.0, z=0.0):
    return LiveState(banc, x, y, z, 0.0)


def test_percent_counts_only_readable(tmp_path):
    hub = StateHub(WORLD, tmp_path)
    snap = hub.update(live("KokiriForest_Child"), "live", SaveState(frozenset({11}), 12, 12, 0.0))
    assert snap["percent"] == 50.0
    assert snap["collected"] == ["11"]


def test_player_position_projected(tmp_path):
    snap = StateHub(WORLD, tmp_path).update(live("KokiriForest_Child", x=10.0, z=-10.0), "live", None)
    assert snap["zone"] == "KokiriForest" and snap["player"] == {"px": 1100.0, "py": 620.0}


def test_dungeon_floor_from_height(tmp_path):
    snap = StateHub(WORLD, tmp_path).update(live("Deku", y=25.0), "live", None)
    assert snap["zone"] == "Deku" and snap["floor"] == 1


def test_unknown_map_keeps_last_zone(tmp_path):
    hub = StateHub(WORLD, tmp_path)
    hub.update(live("KokiriForest_Child"), "live", None)
    snap = hub.update(live("Link_House_Child"), "live", None)
    assert snap["zone"] == "KokiriForest" and snap["banc"] == "KokiriForest_Child" and snap["player"] is None


def test_update_returns_none_when_unchanged(tmp_path):
    hub = StateHub(WORLD, tmp_path)
    assert hub.update(live("KokiriForest_Child"), "live", None) is not None
    assert hub.update(live("KokiriForest_Child"), "live", None) is None


def test_visited_persists(tmp_path):
    hub = StateHub(WORLD, tmp_path)
    hub.update(live("KokiriForest_Child"), "live", None)
    hub.update(live("Deku"), "live", None)
    assert sorted(StateHub(WORLD, tmp_path).snapshot()["visited"]) == ["Deku", "KokiriForest"]


def test_poll_forever_feeds_hub(tmp_path):
    from hookshot_notes.server.state import poll_forever
    from tests.test_save import build_save
    save = tmp_path / "saves" / "acc" / "slot_00" / "progress.sav"
    save.parent.mkdir(parents=True)
    save.write_bytes(build_save(8, 12, [12]))
    hub, stop = StateHub(WORLD, tmp_path), threading.Event()

    class Source:
        status = "live"
        def poll(self):
            stop.set()  # one round is enough
            return live("KokiriForest_Child")
    poll_forever(hub, Source(), tmp_path / "saves", stop, interval=0)
    snap = hub.snapshot()
    assert snap["zone"] == "KokiriForest" and snap["collected"] == ["12"] and snap["status"] == "live"


def test_rejects_non_local_client():
    assert not web.is_local_client("8.8.8.8")
    assert web.is_local_client("192.168.1.20") and web.is_local_client("127.0.0.1") and web.is_local_client("::1")


def _server(tmp_path):
    (tmp_path / "web").mkdir()
    (tmp_path / "web" / "index.html").write_text("<p>ok</p>", "utf-8")
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "world.json").write_text(json.dumps(WORLD), "utf-8")
    hub = StateHub(WORLD, tmp_path / "data")
    srv = web.serve(hub, tmp_path / "data", tmp_path / "web", 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return hub, srv


def test_sse_sends_snapshot_on_connect(tmp_path):
    hub, srv = _server(tmp_path)
    try:
        conn = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=5)
        conn.request("GET", "/events")
        resp = conn.getresponse()
        assert resp.getheader("Content-Type").startswith("text/event-stream")
        line = resp.fp.readline().decode()
        while not line.startswith("data:"):
            line = resp.fp.readline().decode()
        assert json.loads(line[5:]) == hub.snapshot()
        conn.close()
    finally:
        srv.shutdown(); srv.server_close()


def test_routes_and_no_path_traversal(tmp_path):
    hub, srv = _server(tmp_path)
    try:
        port = srv.server_address[1]
        def get(path):
            c = http.client.HTTPConnection("127.0.0.1", port, timeout=5); c.request("GET", path)
            r = c.getresponse(); body = r.read(); c.close(); return r.status, body
        assert get("/")[0] == 200
        assert json.loads(get("/api/world")[1])["bancToZone"]["Deku"] == "Deku"
        assert get("/api/state")[0] == 200
        assert get("/data/../web/index.html")[0] == 404
        assert get("/data/%2e%2e/web/index.html")[0] == 404
        assert get("/nope")[0] == 404
    finally:
        srv.shutdown(); srv.server_close()


def test_poll_forever_survives_a_failing_round(tmp_path):
    from hookshot_notes.server.state import poll_forever
    hub, stop, calls = StateHub(WORLD, tmp_path), threading.Event(), []

    class Source:
        status = "live"
        def poll(self):
            calls.append(1)
            if len(calls) == 1:
                raise FileNotFoundError("save renamed mid-scan")
            stop.set()
            return live("KokiriForest_Child")
    poll_forever(hub, Source(), None, stop, interval=0)
    assert len(calls) == 2 and hub.snapshot()["zone"] == "KokiriForest"


def test_failed_save_read_is_retried(tmp_path, monkeypatch):
    from hookshot_notes.game import save as save_mod
    from hookshot_notes.server.state import poll_forever
    from tests.test_save import build_save
    p = tmp_path / "saves" / "acc" / "slot_00" / "progress.sav"
    p.parent.mkdir(parents=True)
    p.write_bytes(build_save(8, 12, [12]))
    real, attempts = save_mod.SaveReader.read, []

    def flaky(self, path):
        attempts.append(1)
        return None if len(attempts) == 1 else real(self, path)  # first read hits a sharing violation
    monkeypatch.setattr(save_mod.SaveReader, "read", flaky)
    hub, stop, rounds = StateHub(WORLD, tmp_path), threading.Event(), []

    class Source:
        status = "live"
        def poll(self):
            rounds.append(1)
            if len(rounds) == 3:
                stop.set()
            return live("KokiriForest_Child")
    poll_forever(hub, Source(), tmp_path / "saves", stop, interval=0)
    assert hub.snapshot()["collected"] == ["12"]


def test_last_zone_restored_on_start(tmp_path):
    StateHub(WORLD, tmp_path).update(live("KokiriForest_Child"), "live", None)
    snap = StateHub(WORLD, tmp_path).snapshot()
    assert snap["zone"] == "KokiriForest" and snap["banc"] == "KokiriForest_Child" and snap["player"] is None


def test_second_server_on_same_port_fails(tmp_path):
    import pytest
    hub = StateHub(WORLD, tmp_path)
    first = web.serve(hub, tmp_path, tmp_path, 0)
    try:
        with pytest.raises(OSError):
            web.serve(hub, tmp_path, tmp_path, first.server_address[1])
    finally:
        first.server_close()
