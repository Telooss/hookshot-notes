import ctypes
import subprocess
import sys

from ..formats.nso import build_id
from ..game.memory import find_game_pid
from ..paths import GameDir

KNOWN_BUILD_ID = "e0f3ccfaf50065ae4ea01eb5aeb13b1a45da3348"  # Ocarina of Time (Switch 2), update 2.0.0


def check_version(game: GameDir) -> str | None:
    """None when the game build is the analysed one, else a message for the player."""
    try:
        bid = build_id(game.exefs_main)
    except (OSError, ValueError):
        return "Fichiers du jeu introuvables : place Hookshot Notes dans le dossier Hookshot."
    if bid == KNOWN_BUILD_ID:
        return None
    return (f"Version du jeu non reconnue (build {bid}). Hookshot Notes fonctionne avec la mise à jour 2.0.0. "
            "La carte reste consultable sans position en direct.")


def ensure_running(game: GameDir) -> None:
    """Start the game through Hookshot's own launcher, unless it is already running."""
    if find_game_pid() is None and game.launcher.is_file():
        if getattr(sys, "frozen", False):  # don't hand PyInstaller's temp DLL folder down to the game
            ctypes.windll.kernel32.SetDllDirectoryW(None)
        subprocess.Popen([str(game.launcher)], cwd=str(game.root))
