"""Hero and item lists from Valve's Dota 2 datafeed (the API dota2.com itself uses)."""

from __future__ import annotations

import functools
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, TypedDict

import requests

from .logs import logger

if TYPE_CHECKING:

    class DatafeedHero(TypedDict):
        id: int
        name: str
        name_loc: str
        name_english_loc: str
        primary_attr: int
        complexity: int

    class DatafeedItem(TypedDict):
        id: int
        name: str
        name_loc: str
        name_english_loc: str


__all__ = (
    "Hero",
    "PrimaryAttribute",
    "get_heroes",
    "get_item_names",
)

DATAFEED_URL = "https://www.dota2.com/datafeed"

type PrimaryAttribute = Literal["str", "agi", "int", "all"]
PRIMARY_ATTRIBUTES: dict[int, PrimaryAttribute] = {0: "str", 1: "agi", 2: "int", 3: "all"}


@dataclass(frozen=True, slots=True)
class Hero:
    """A hero from the datafeed.

    Attributes
    ----------
    id:
        Dota 2 hero ID.
    npc_name:
        Valve's internal name, i.e. `"npc_dota_hero_crystal_maiden"`.
    localized_name:
        English name, i.e. `"Crystal Maiden"`.
    primary_attribute:
        `"str"`, `"agi"`, `"int"` or `"all"` (universal).
    """

    id: int
    npc_name: str
    localized_name: str
    primary_attribute: PrimaryAttribute

    @property
    def slug_name(self) -> str:
        """Valve's short name, i.e. `"crystal_maiden"`. Guide files are named after it."""
        return self.npc_name.removeprefix("npc_dota_hero_")

    def __str__(self) -> str:
        return self.localized_name


def _get(endpoint: str, attempts: int = 3) -> Any:
    """GET a datafeed endpoint, retrying a few times - dota2.com likes to time out on the first request."""
    url = f"{DATAFEED_URL}/{endpoint}"
    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(url, params={"language": "english"}, timeout=20)
            response.raise_for_status()
            return response.json()["result"]["data"]
        except requests.ConnectionError, requests.Timeout:
            if attempt == attempts:
                raise
            logger.warning("⏳ dota2.com datafeed: attempt #{} for {} failed, retrying", attempt, endpoint)
            time.sleep(2.0 * attempt)
    return None  # unreachable, `range` always has at least one attempt


@functools.cache
def get_heroes() -> dict[int, Hero]:
    """All heroes keyed by hero ID. Fetched once per run."""
    heroes: list[DatafeedHero] = _get("herolist")["heroes"]
    return {
        hero["id"]: Hero(
            id=hero["id"],
            npc_name=hero["name"],
            localized_name=hero["name_english_loc"],
            primary_attribute=PRIMARY_ATTRIBUTES[hero["primary_attr"]],
        )
        for hero in heroes
    }


@functools.cache
def get_item_names() -> dict[int, str]:
    """Item ID -> Valve item name, i.e. `1: "item_blink"`. Fetched once per run."""
    items: list[DatafeedItem] = _get("itemlist")["itemabilities"]
    return {item["id"]: item["name"] for item in items}
