from pathlib import Path

from hookshot_notes.launcher import game, qr, shortcut
from hookshot_notes.paths import GameDir


def test_wrong_build_id_message(tmp_path):
    (tmp_path / ".hookshot_exefs").mkdir()
    (tmp_path / ".hookshot_exefs" / "main").write_bytes(b"NSO0" + bytes(0x3C) + bytes(range(20)) + bytes(16))
    msg = game.check_version(GameDir(tmp_path))
    assert "non reconnue" in msg and bytes(range(20)).hex() in msg


def test_known_build_id_has_no_message(tmp_path):
    (tmp_path / ".hookshot_exefs").mkdir()
    bid = bytes.fromhex(game.KNOWN_BUILD_ID)
    (tmp_path / ".hookshot_exefs" / "main").write_bytes(b"NSO0" + bytes(0x3C) + bid + bytes(16))
    assert game.check_version(GameDir(tmp_path)) is None


def test_shortcut_command_quotes_paths():
    script = shortcut.shortcut_script(Path(r"C:\Jeux d'Ami\Hookshot\hookshot-notes.exe"), "Hookshot Notes")
    assert r"'C:\Jeux d''Ami\Hookshot\hookshot-notes.exe'" in script
    assert r"'C:\Jeux d''Ami\Hookshot'" in script  # working directory
    assert "'Hookshot Notes.lnk'" in script
    assert "Test-Path" in script  # never replaces an existing shortcut


def test_qr_svg():
    out = qr.svg("http://192.168.1.5:8737/")
    assert out.lstrip().startswith(("<svg", "<?xml"))
