"""Finds the player's Hookshot folder, so hookshot-notes.exe can live anywhere."""
from __future__ import annotations

import json
from pathlib import Path

from ..paths import GameDir

CONFIG = Path("HookshotNotes") / "config.json"
BUILDER_SETTINGS = Path("HookshotBuilder") / "builder-settings.json"  # written by the Hookshot builder ("Out" = game folder)


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text("utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def find_game_dir(explicit: Path | None, exe_dir: Path, local_appdata: Path) -> GameDir | None:
    """--game-dir, then the exe's own folder, then the folder used last time, then the Hookshot builder's output."""
    candidates = [explicit, exe_dir,
                  _read_json(local_appdata / CONFIG).get("game_dir"),
                  _read_json(local_appdata / BUILDER_SETTINGS).get("Out")]
    for c in candidates:
        if c:
            game = GameDir.find(Path(c))
            if game:
                return game
    return None


def remember(local_appdata: Path, game_root: Path) -> None:
    path = local_appdata / CONFIG
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"game_dir": str(game_root)}), "utf-8")
    except OSError:
        pass  # asked again next time


def ask_game_dir() -> Path | None:
    """Folder picker, shown only when nothing was found."""
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        return None
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    chosen = filedialog.askdirectory(title="Hookshot Notes : choisis ton dossier Hookshot (celui qui contient romfs)")
    root.destroy()
    return Path(chosen) if chosen else None
