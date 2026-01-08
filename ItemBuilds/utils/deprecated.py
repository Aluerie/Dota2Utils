"""
We should delete this code but
I'm being lazy.
"""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, TypedDict

import requests

from .api import backup, restore

if TYPE_CHECKING:

    class OpendotaConstantsHero(TypedDict):
        id: int
        name: str
        primary_attr: Literal["str", "agi", "int", "all"]
        img: str
        localized_name: str

    class OpendotaConstantsItem(TypedDict):
        cost: int


log = logging.getLogger(__name__)


@dataclass
class Item:
    key: str
    cost: int

    @property
    def item_key(self) -> str:
        return f"item_{self.key}"

    def __repr__(self) -> str:
        return f"<class Item key={self.key}>"


def fetch_items() -> dict[str, Item]:
    endpoint = "https://api.opendota.com/api/constants/items"
    response = requests.get(endpoint, timeout=20)
    data: dict[str, OpendotaConstantsItem] = response.json()

    return {
        key: Item(
            key=key,
            cost=item["cost"],
        )
        for key, item in data.items()
    }


def get_or_fetch_items(*, force: bool = False) -> dict[str, Item]:
    restored = restore("items")

    now = datetime.datetime.now(tz=datetime.UTC)
    last_updated = datetime.datetime.fromisoformat(restored["last_updated"])
    if not force and now - last_updated < datetime.timedelta(days=1):
        # API rate limit measures
        log.debug("Using the backup for items data.")
        return {item["key"]: Item(key=item["key"], cost=item["cost"]) for item in restored["data"].values()}

    log.debug("Fetching items data from OpenDota.")
    to_backup = fetch_items()
    backup("items", to_backup)
    return to_backup
