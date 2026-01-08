from __future__ import annotations

import datetime
import json
import logging
import pathlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, TypedDict

import requests

if TYPE_CHECKING:

    class OpendotaConstantsHero(TypedDict):
        id: int
        name: str
        primary_attr: Literal["str", "agi", "int", "all"]
        img: str
        localized_name: str


log = logging.getLogger(__name__)
__all__ = (
    "Hero",
    "get_or_fetch_heroes",
)


@dataclass
class Hero:
    id: int
    slug_name: str
    loc_name: str

    def __repr__(self) -> str:
        return f"<class Hero id={self.id} name={self.loc_name}>"


def fetch_heroes() -> dict[int, Hero]:
    endpoint = "https://api.opendota.com/api/constants/heroes"
    response = requests.get(endpoint, timeout=20)
    data: dict[str, OpendotaConstantsHero] = response.json()

    return {
        hero["id"]: Hero(
            id=hero["id"],
            slug_name=hero["name"].removeprefix("npc_dota_hero_"),
            loc_name=hero["localized_name"],
        )
        for _, hero in data.items()
    }


def backup(name: str, data: dict[Any, Any]) -> None:
    backup: dict[str, Any] = {
        "last_updated": datetime.datetime.now(tz=datetime.UTC),
        "data": {key: value.__dict__ for key, value in data.items()},
    }
    with pathlib.Path(f"data/backup_{name}.json").open("w", encoding="utf-8") as f:
        json.dump(backup, f, ensure_ascii=False, indent=4, default=str)


def restore(name: str) -> dict[str, Any]:
    with pathlib.Path(f"data/backup_{name}.json").open(encoding="utf-8") as f:
        return json.load(f)


def get_or_fetch_heroes(*, force: bool = False) -> dict[int, Hero]:
    restored = restore("heroes")

    now = datetime.datetime.now(tz=datetime.UTC)
    last_updated = datetime.datetime.fromisoformat(restored["last_updated"])
    if not force and now - last_updated < datetime.timedelta(days=1):
        # API rate limit measures
        log.debug("Using the backup for heroes data.")
        return {
            hero["id"]: Hero(id=hero["id"], slug_name=hero["slug_name"], loc_name=hero["loc_name"])
            for hero in restored["data"].values()
        }

    log.debug("Fetching heroes data from OpenDota.")
    to_backup = fetch_heroes()
    backup("heroes", to_backup)
    return to_backup
