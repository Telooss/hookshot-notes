"""Manual check of the page without the game: python -m tests.manual.demo_server <cache dir> <banc> [port]
(build the cache once with hookshot_notes.extract.run.extract)."""
import json
import sys
import threading
from pathlib import Path

from hookshot_notes.server import http as web
from hookshot_notes.server.state import DemoSource, StateHub, poll_forever

data = Path(sys.argv[1])
world = json.loads((data / "world.json").read_text("utf-8"))
hub = StateHub(world, data)
threading.Thread(target=poll_forever, args=(hub, DemoSource(world, sys.argv[2]), None, threading.Event()), daemon=True).start()
srv = web.serve(hub, data, Path(web.__file__).parent.parent / "web", int(sys.argv[3]) if len(sys.argv) > 3 else 8737)
print("demo on", web.lan_url(srv.server_address[1]), flush=True)
srv.serve_forever()
