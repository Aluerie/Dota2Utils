"""Names of the pro teams behind the "team fandom" emoticon categories (`teamfandom_<season>_<team id>`).

Valve's files only name some of the teams, so the rest are looked up on dota2.com and remembered in
`team_names.json`, so every team is looked up only once (teams it doesn't know are remembered as `null`).
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from typing import TYPE_CHECKING

import requests

from dota2utils_common.logs import logger

if TYPE_CHECKING:
    import pathlib

    from .main import EmoticonsCategory
    from .vpk_files import VPKFiles

__all__ = (
    "TEAM_CATEGORY",
    "category_title",
    "resolve_team_names",
)

TEAM_CATEGORY = re.compile(r"teamfandom_(?P<season>\d+)_(?P<team_id>\d+)")
ITEMS_LOCALIZATION = "resource/localization/items_english.txt"
TEAM_INFO_CACHE = "team_info_cache.json"
# "DOTA_Item_TeamSticker_Season10_8291895"  "Tundra Esports Team Sticker - TI 2023"
TEAM_STICKER = re.compile(r'"DOTA_Item_TeamSticker(?:Champion)?_Season(\d+)_(\d+)"\s+"(.+?) Team Sticker[^"]*"')
TEAM_INFO_URL = "https://www.dota2.com/webapi/IDOTA2Teams/GetSingleTeamInfo/v001"
# dota2.com is slow and often times out, so be patient and gentle with it;
REQUEST_TIMEOUT = 60
REQUEST_ATTEMPTS = 2
PAUSE_BETWEEN_REQUESTS = 1.0


def category_title(name: str, category: EmoticonsCategory, team_names: dict[int, str]) -> str:
    """Heading for an emoticon category: `Team fandom: Tundra Esports (season 5)` for team categories."""
    match = TEAM_CATEGORY.fullmatch(name)
    if match is None:
        return name.capitalize()
    team_id, season = int(match["team_id"]), match["season"]
    team = team_names.get(team_id) or team_tag(category) or str(team_id)
    return f"Team fandom: {' '.join(team.split())} (season {season})"  # some names come with stray spaces;


def team_tag(category: EmoticonsCategory) -> str | None:
    """The team tag from the category's emoticon aliases, i.e. `TUN` from `fandom_TUN_5_0`."""
    for emote in category["emoticons"].values():
        parts = emote["aliases"]["0"].split("_")
        if len(parts) >= 3 and parts[0] == "fandom":  # `fandom_<tag>_<season>_<index>`
            return parts[1]
    return None


def decode_text(data: bytes) -> str:
    """Valve's text files are UTF-8 or UTF-16 (with a byte order mark)."""
    return data.decode("utf-16" if data[:2] in {b"\xff\xfe", b"\xfe\xff"} else "utf-8-sig", errors="replace")


def names_from_stickers(localization: str) -> dict[int, str]:
    """Team names from team sticker items; a team's newest sticker wins (teams get renamed)."""
    newest: dict[int, tuple[int, str]] = {}
    for season, team_id, name in TEAM_STICKER.findall(localization):
        if int(season) >= newest.get(int(team_id), (-1, ""))[0]:
            newest[int(team_id)] = (int(season), name)
    return {team_id: name for team_id, (_, name) in newest.items()}


def names_from_team_info(data: bytes) -> dict[int, str]:
    """Team names from the game's team info cache (the current TI teams)."""
    # The file is JSON followed by a NUL byte;
    cache, _ = json.JSONDecoder().raw_decode(decode_text(data))
    return {team["team_id"]: team["name"] for team in cache["team_list"]["teams"] if team.get("name")}


def fetch_team_name(team_id: int) -> str | None:
    """The team's name from dota2.com, or `None` if it has none or dota2.com doesn't answer."""
    for attempt in range(1, REQUEST_ATTEMPTS + 1):
        try:
            response = requests.get(TEAM_INFO_URL, params={"team_id": team_id}, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json().get("name") or None
        except (requests.RequestException, ValueError) as exc:
            logger.warning("⏳ dota2.com: team {} lookup attempt #{} failed ({})", team_id, attempt, type(exc).__name__)
            time.sleep(5.0 * attempt)
    return None


def load_cache(path: pathlib.Path) -> dict[int, str | None]:
    """Team ID -> name from dota2.com, `None` for teams it had no name for (delete such a line to look it up again)."""
    if not path.is_file():
        return {}
    return {int(team_id): name for team_id, name in json.loads(path.read_text(encoding="utf-8")).items()}


def save_cache(path: pathlib.Path, names: dict[int, str | None]) -> None:
    text = json.dumps({str(team_id): names[team_id] for team_id in sorted(names)}, ensure_ascii=False, indent=4)
    path.write_text(text + "\n", encoding="utf-8", newline="\n")


async def resolve_team_names(
    files: VPKFiles, data: dict[str, EmoticonsCategory], cache_path: pathlib.Path
) -> dict[int, str]:
    """Names of the teams that have emoticon categories in `data`: from Valve's files, else dota2.com (cached)."""
    team_ids = {int(match["team_id"]) for name in data if (match := TEAM_CATEGORY.fullmatch(name))}
    if not team_ids:
        return {}

    contents = await files.read_many([ITEMS_LOCALIZATION, TEAM_INFO_CACHE])
    names: dict[int, str] = {}
    if ITEMS_LOCALIZATION in contents:
        names |= names_from_stickers(decode_text(contents[ITEMS_LOCALIZATION]))
    if TEAM_INFO_CACHE in contents:
        names |= names_from_team_info(contents[TEAM_INFO_CACHE])

    cache = load_cache(cache_path)
    unknown = sorted(team_ids - names.keys() - cache.keys())
    if unknown:
        logger.info("🌐 Looking up {} team names on dota2.com", len(unknown))
        for team_id in unknown:
            # Misses are remembered too: dota2.com takes ~40s to give up on old teams, so ask about each only once;
            cache[team_id] = await asyncio.to_thread(fetch_team_name, team_id)
            save_cache(cache_path, cache)  # after every team, so an interrupted run keeps what it found;
            await asyncio.sleep(PAUSE_BETWEEN_REQUESTS)

    # Valve's files are the most current; the cache only fills the gaps;
    return {team_id: name for team_id in team_ids if (name := names.get(team_id) or cache.get(team_id))}
