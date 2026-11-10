"""hookshot-notes.exe: first-run extraction, shortcut, local server, browser, game.

python -m hookshot_notes [--port N] [--no-game] [--demo BANC] [--game-dir PATH]"""
import argparse
import json
import os
import sys
import threading
import webbrowser
from pathlib import Path

from .extract.run import cache_is_valid, extract
from .formats.nso import build_id
from .game.live import Tracker
from .game.memory import open_game_memory
from .launcher import game as launcher
from .launcher import qr
from .launcher.locate import ask_game_dir, find_game_dir, remember
from .launcher.shortcut import create_desktop_shortcut
from .paths import GameDir
from .server import http as web
from .server.state import DemoSource, StateHub, poll_forever

DEFAULT_PORT = 8737


class _NoLive:
    """Unknown game version: the map works, the live position stays off."""
    status = "unsupported"

    def poll(self):
        return None


def _here() -> Path:
    return Path(sys.executable).parent if getattr(sys, "frozen", False) else Path.cwd()


def _progress(step: str, frac: float) -> None:
    print(f"\r  {step:<10} {int(frac * 100):3d} %", end="", flush=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="hookshot-notes")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--no-game", action="store_true", help="ne pas lancer le jeu")
    ap.add_argument("--demo", metavar="BANC", help="Link de démonstration dans cette carte (ex. KokiriForest_Child)")
    ap.add_argument("--game-dir", type=Path)
    args = ap.parse_args(argv)

    appdata = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    game = find_game_dir(args.game_dir, _here(), appdata)
    if game is None:
        print("Dossier Hookshot introuvable : choisis-le dans la fenêtre qui s'ouvre.")
        chosen = ask_game_dir()
        game = GameDir.find(chosen) if chosen else None
    if game is None:
        print("Dossier Hookshot introuvable : choisis le dossier qui contient romfs et hookshot.exe.")
        input("Entrée pour fermer…")
        return 1
    remember(appdata, game.root)
    print("Jeu :", game.root)
    problem = launcher.check_version(game)
    if problem:
        print(problem)

    data = game.root / "hookshot-notes-data"
    first_run = not data.exists()
    try:
        bid = build_id(game.exefs_main)
    except (OSError, ValueError):
        bid = ""
    if not cache_is_valid(data, bid):
        print("Préparation des cartes depuis ta copie du jeu (une seule fois)…")
        extract(game, data, _progress)
        print()
    if first_run and getattr(sys, "frozen", False):
        try:
            print("Raccourci créé :", create_desktop_shortcut(Path(sys.executable)))
        except Exception as e:  # the map works without the shortcut
            print("Raccourci non créé :", e)

    world = json.loads((data / "world.json").read_text("utf-8"))
    hub = StateHub(world, data)
    if args.demo:
        source = DemoSource(world, args.demo)
    elif problem:
        source = _NoLive()
    else:
        source = Tracker(open_game_memory, set(world["bancToZone"]))

    try:
        srv = web.serve(hub, data, Path(__file__).parent / "web", args.port)
    except OSError:
        srv = web.serve(hub, data, Path(__file__).parent / "web", 0)
    port = srv.server_address[1]
    url = web.lan_url(port)
    srv.extra_routes["/api/qr"] = lambda: (json.dumps({"url": url, "svg": qr.svg(url)}).encode(), "application/json")

    stop = threading.Event()
    threading.Thread(target=poll_forever, args=(hub, source, game.saves, stop), daemon=True).start()
    print(f"Hookshot Notes : {url}  (sur ce PC : http://localhost:{port}/)")
    print("Laisse cette fenêtre ouverte pendant que tu joues.")
    webbrowser.open(f"http://localhost:{port}/")
    if not (args.no_game or args.demo):
        launcher.ensure_running(game)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        srv.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
