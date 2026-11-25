"""Locate Steam, the Steam account (Friend ID) and Dota 2 folders on this machine."""

from __future__ import annotations

import pathlib
import sys

import vdf

from .config import section
from .errors import SteamNotFoundError

__all__ = (
    "DOTA_APP_ID",
    "cfg_dir",
    "dota_path",
    "friend_id",
    "guides_dir",
    "parse_library_folders",
    "steam_path",
    "userdata_accounts",
)

DOTA_APP_ID = 570
DEFAULT_STEAM_PATH = pathlib.Path(r"C:\Program Files (x86)\Steam")


def _registry_value(key: str, name: str) -> object | None:
    """Read a value from `HKEY_CURRENT_USER`, or `None` if it does not exist (or we're not on Windows)."""
    if sys.platform != "win32":
        return None

    import winreg  # ruff: ignore[import-outside-top-level] # Windows-only module

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as handle:
            return winreg.QueryValueEx(handle, name)[0]
    except OSError:
        return None


def steam_path() -> pathlib.Path:
    """Steam install folder: `[steam].path` from config, else the Windows registry, else the default location."""
    if configured := section("steam").get("path"):
        return pathlib.Path(configured)

    from_registry = _registry_value(r"Software\Valve\Steam", "SteamPath")
    if isinstance(from_registry, str) and pathlib.Path(from_registry).is_dir():
        return pathlib.Path(from_registry)

    if DEFAULT_STEAM_PATH.is_dir():
        return DEFAULT_STEAM_PATH

    msg = "Could not find the Steam install folder. Set `path` under `[steam]` in config.toml."
    raise SteamNotFoundError(msg)


def userdata_accounts(steam: pathlib.Path) -> list[int]:
    """Steam32 IDs of the accounts that have a folder in `Steam/userdata` (`0` is a placeholder Steam creates)."""
    userdata = steam / "userdata"
    if not userdata.is_dir():
        return []
    return sorted(int(p.name) for p in userdata.iterdir() if p.is_dir() and p.name.isdigit() and p.name != "0")


def friend_id(steam: pathlib.Path | None = None) -> int:
    """Steam32 ID ("Friend ID") of the account to work with.

    Uses `[steam].friend_id` from config, else the account currently logged into Steam,
    else the only account in `Steam/userdata`.
    """
    configured = section("steam").get("friend_id")
    if configured is not None:
        return int(configured)

    active = _registry_value(r"Software\Valve\Steam\ActiveProcess", "ActiveUser")
    if isinstance(active, int) and active != 0:
        return active

    accounts = userdata_accounts(steam or steam_path())
    if len(accounts) == 1:
        return accounts[0]

    found = ", ".join(map(str, accounts)) or "none"
    msg = (
        f"Could not work out which Steam account to use (accounts found in Steam/userdata: {found}). "
        "Log into Steam or set `friend_id` under `[steam]` in config.toml."
    )
    raise SteamNotFoundError(msg)


def _dota_remote_dir() -> pathlib.Path:
    steam = steam_path()
    return steam / "userdata" / str(friend_id(steam)) / str(DOTA_APP_ID) / "remote"


def guides_dir() -> pathlib.Path:
    """Folder with the Dota 2 hero guide (`.build`) files of the current account."""
    return _dota_remote_dir() / "guides"


def cfg_dir() -> pathlib.Path:
    """Folder with the Dota 2 cloud config files (i.e. `hero_grid_config.json`) of the current account."""
    return _dota_remote_dir() / "cfg"


def parse_library_folders(text: str) -> list[tuple[pathlib.Path, set[str]]]:
    """Parse `steamapps/libraryfolders.vdf` into `(library path, app ids installed there)` pairs."""
    data = vdf.loads(text)
    folders = data.get("libraryfolders") or data.get("LibraryFolders") or {}
    libraries: list[tuple[pathlib.Path, set[str]]] = []
    for value in folders.values():
        if isinstance(value, dict) and "path" in value:
            apps = value.get("apps") or {}
            libraries.append((pathlib.Path(value["path"]), set(apps)))
        elif isinstance(value, str) and ("\\" in value or "/" in value):
            # Old format: `"1" "D:\\SteamLibrary"` without the list of apps;
            libraries.append((pathlib.Path(value), set()))
    return libraries


def dota_path() -> pathlib.Path:
    """Dota 2 install folder (`.../steamapps/common/dota 2 beta`), searched across all Steam libraries."""
    steam = steam_path()
    libraries = [(steam, set[str]())]
    library_file = steam / "steamapps" / "libraryfolders.vdf"
    if library_file.is_file():
        libraries = parse_library_folders(library_file.read_text(encoding="utf-8")) or libraries

    # Libraries that say they have Dota installed go first;
    libraries.sort(key=lambda lib: str(DOTA_APP_ID) not in lib[1])
    for library, _ in libraries:
        candidate = library / "steamapps" / "common" / "dota 2 beta"
        if candidate.is_dir():
            return candidate

    msg = f"Could not find a Dota 2 install in these Steam libraries: {[str(lib) for lib, _ in libraries]}"
    raise SteamNotFoundError(msg)
