from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GameDir:
    """A built Hookshot folder (romfs + exefs extracted from the player's own cartridge)."""
    root: Path

    @property
    def romfs(self) -> Path: return self.root / "romfs"
    @property
    def exefs_main(self) -> Path: return self.root / ".hookshot_exefs" / "main"
    @property
    def launcher(self) -> Path: return self.root / "hookshot.exe"
    @property
    def saves(self) -> Path: return self.root / "user" / "save"
    @property
    def language_file(self) -> Path: return self.root / "language.txt"

    @staticmethod
    def find(start: Path) -> GameDir | None:
        """Walk up from `start` to the first folder holding both romfs/ and .hookshot_exefs/."""
        for d in [start.resolve(), *start.resolve().parents]:
            if (d / "romfs").is_dir() and (d / ".hookshot_exefs").is_dir():
                return GameDir(d)
        return None
