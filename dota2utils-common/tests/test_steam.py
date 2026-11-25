from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from dota2utils_common import SteamNotFoundError, steam

if TYPE_CHECKING:
    import pathlib


@pytest.fixture
def fake_steam(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> pathlib.Path:
    """An empty Steam folder, with the Windows registry pretending Steam is not logged in."""
    root = tmp_path / "Steam"
    (root / "userdata" / "0").mkdir(parents=True)  # Steam creates this placeholder;
    monkeypatch.setattr(steam, "_registry_value", lambda _key, _name: None)
    monkeypatch.setattr(steam, "steam_path", lambda: root)
    return root


def test_friend_id_from_single_userdata_account(fake_steam: pathlib.Path) -> None:
    (fake_steam / "userdata" / "112233").mkdir()
    assert steam.friend_id() == 112233


def test_friend_id_ambiguous(fake_steam: pathlib.Path) -> None:
    (fake_steam / "userdata" / "111").mkdir()
    (fake_steam / "userdata" / "222").mkdir()
    with pytest.raises(SteamNotFoundError, match="111, 222"):
        steam.friend_id()


def test_friend_id_prefers_logged_in_user(fake_steam: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (fake_steam / "userdata" / "111").mkdir()
    (fake_steam / "userdata" / "222").mkdir()
    monkeypatch.setattr(steam, "_registry_value", lambda _key, name: 222 if name == "ActiveUser" else None)
    assert steam.friend_id() == 222


def test_friend_id_from_config_wins(fake_steam: pathlib.Path, isolated_config: pathlib.Path) -> None:
    (fake_steam / "userdata" / "111").mkdir()
    isolated_config.write_text("[steam]\nfriend_id = 999\n", encoding="utf-8")
    assert steam.friend_id() == 999


def test_guides_dir(fake_steam: pathlib.Path) -> None:
    (fake_steam / "userdata" / "112233").mkdir()
    assert steam.guides_dir() == fake_steam / "userdata" / "112233" / "570" / "remote" / "guides"


LIBRARY_FOLDERS = r"""
"libraryfolders"
{
	"0"
	{
		"path"		"C:\\Program Files (x86)\\Steam"
		"apps"
		{
			"228980"		"1234"
		}
	}
	"1"
	{
		"path"		"D:\\SteamLibrary"
		"apps"
		{
			"570"		"77346294160"
		}
	}
}
"""


def test_parse_library_folders() -> None:
    libraries = steam.parse_library_folders(LIBRARY_FOLDERS)
    assert [(str(path), apps) for path, apps in libraries] == [
        (r"C:\Program Files (x86)\Steam", {"228980"}),
        (r"D:\SteamLibrary", {"570"}),
    ]


def test_dota_path_searches_libraries(fake_steam: pathlib.Path, tmp_path: pathlib.Path) -> None:
    library = tmp_path / "SteamLibrary"
    dota = library / "steamapps" / "common" / "dota 2 beta"
    dota.mkdir(parents=True)
    (fake_steam / "steamapps").mkdir()
    (fake_steam / "steamapps" / "libraryfolders.vdf").write_text(
        LIBRARY_FOLDERS.replace(r"D:\\SteamLibrary", str(library).replace("\\", "\\\\")), encoding="utf-8"
    )
    assert steam.dota_path() == dota
