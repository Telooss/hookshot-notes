import json

from hookshot_notes.launcher.locate import find_game_dir, remember


def make_game(path):
    (path / "romfs").mkdir(parents=True)
    (path / ".hookshot_exefs").mkdir()
    return path


def test_prefers_explicit_then_exe_folder(tmp_path):
    a, b = make_game(tmp_path / "A"), make_game(tmp_path / "B")
    assert find_game_dir(a, b, tmp_path / "appdata").root == a.resolve()
    assert find_game_dir(None, b / "sub", tmp_path / "appdata").root == b.resolve()


def test_uses_remembered_folder(tmp_path):
    game = make_game(tmp_path / "Games" / "Hookshot")
    appdata = tmp_path / "appdata"
    remember(appdata, game)
    assert find_game_dir(None, tmp_path / "Downloads", appdata).root == game.resolve()


def test_uses_hookshot_builder_output(tmp_path):
    game = make_game(tmp_path / "Games" / "Hookshot")
    appdata = tmp_path / "appdata"
    (appdata / "HookshotBuilder").mkdir(parents=True)
    (appdata / "HookshotBuilder" / "builder-settings.json").write_text(json.dumps({"Out": str(game), "Nup": "x"}), "utf-8")
    assert find_game_dir(None, tmp_path / "Downloads", appdata).root == game.resolve()


def test_ignores_stale_or_broken_settings(tmp_path):
    appdata = tmp_path / "appdata"
    (appdata / "HookshotBuilder").mkdir(parents=True)
    (appdata / "HookshotBuilder" / "builder-settings.json").write_text("{not json", "utf-8")
    remember(appdata, tmp_path / "deleted-folder")
    assert find_game_dir(None, tmp_path / "Downloads", appdata) is None
