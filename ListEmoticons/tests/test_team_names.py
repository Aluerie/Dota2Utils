from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any

from list_emoticons import team_names

if TYPE_CHECKING:
    import pathlib
    from collections.abc import Iterable

    import pytest

STICKERS = """
"lang"
{
    "Tokens"
    {
        "DOTA_Item_TeamSticker_Season6_100"        "Old Name Team Sticker - TI 2022"
        "DOTA_Item_TeamSticker_Season10_100"       "New Name Team Sticker - TI 2023"
        "DOTA_Item_TeamStickerChampion_Season6_200"    "Champs Team Sticker - TI 2022 Champion"
        "DOTA_Item_TeamSticker_Season6_200_desc"   "Champs Team Sticker"
    }
}
"""
TEAM_INFO = json.dumps({"team_list": {"teams": [{"team_id": 300, "name": "Cached Team", "tag": "CT"}]}})


def category(tag: str = "TUN") -> Any:
    alias = f"fandom_{tag}_5_0"
    return {"utf": "utf-8", "path": "", "emoticons": {"1": {"image_name": "a.png", "aliases": {"0": alias}}}}


class FakeFiles:
    def __init__(self, files: dict[str, bytes]) -> None:
        self.files = files

    async def read_many(self, paths: Iterable[str]) -> dict[str, bytes]:
        return {path: self.files[path] for path in paths if path in self.files}


def test_names_from_stickers_prefers_newest_season() -> None:
    assert team_names.names_from_stickers(STICKERS) == {100: "New Name", 200: "Champs"}


def test_names_from_team_info_ignores_trailing_nul() -> None:
    assert team_names.names_from_team_info(TEAM_INFO.encode() + b"\x00") == {300: "Cached Team"}


def test_category_title() -> None:
    assert team_names.category_title("default", category(), {}) == "Default"
    assert team_names.category_title("teamfandom_5_100", category(), {100: "Tundra"}) == "Team fandom: Tundra (season 5)"
    # Unknown team: the tag from the aliases, else the ID;
    assert team_names.category_title("teamfandom_5_100", category("TUN"), {}) == "Team fandom: TUN (season 5)"
    no_tag: Any = {"utf": "", "path": "", "emoticons": {"1": {"aliases": {"0": "smile"}}}}
    assert team_names.category_title("teamfandom_7_100", no_tag, {}) == "Team fandom: 100 (season 7)"


def test_resolve_team_names(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cache_path = tmp_path / "team_names.json"
    cache_path.write_text('{"400": "Remembered"}', encoding="utf-8")
    looked_up: list[int] = []

    def fake_fetch(team_id: int) -> str | None:
        looked_up.append(team_id)
        return {500: "From dota2.com"}.get(team_id)

    monkeypatch.setattr(team_names, "fetch_team_name", fake_fetch)
    monkeypatch.setattr(team_names, "PAUSE_BETWEEN_REQUESTS", 0)
    files = FakeFiles({
        team_names.ITEMS_LOCALIZATION: STICKERS.encode("utf-16"),  # localization files are UTF-16;
        team_names.TEAM_INFO_CACHE: TEAM_INFO.encode(),
    })
    data: Any = {f"teamfandom_5_{team_id}": category() for team_id in (100, 300, 400, 500, 600)}
    data["default"] = category()

    names = asyncio.run(team_names.resolve_team_names(files, data, cache_path))

    assert names == {100: "New Name", 300: "Cached Team", 400: "Remembered", 500: "From dota2.com"}
    assert looked_up == [500, 600]  # only teams nobody knows yet;
    # Misses are remembered too, so they aren't looked up again;
    assert json.loads(cache_path.read_text(encoding="utf-8")) == {"400": "Remembered", "500": "From dota2.com", "600": None}
    looked_up.clear()
    asyncio.run(team_names.resolve_team_names(files, data, cache_path))
    assert looked_up == []
