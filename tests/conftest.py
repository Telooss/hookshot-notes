import os
from pathlib import Path

import pytest

from hookshot_notes.paths import GameDir


@pytest.fixture(scope="session")
def game_dir() -> GameDir:
    """The player's own Hookshot folder; tests marked `game` are skipped without it."""
    root = os.environ.get("HOOKSHOT_DIR")
    if not root:
        pytest.skip("HOOKSHOT_DIR non défini")
    game = GameDir.find(Path(root))
    if game is None:
        pytest.skip(f"pas de dossier Hookshot dans {root}")
    return game
