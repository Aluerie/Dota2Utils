from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, TypedDict

import requests

if TYPE_CHECKING:

    class OpendotaConstantsHero(TypedDict):
        id: int
        name: str
        primary_attr: Literal["str", "agi", "int", "all"]
        img: str
        localized_name: str


__all__ = ("heroes",)


@dataclass
class Hero:
    id: int
    name: str
    npc_name: str
    icon: str
    primary_attribute: Literal["str", "agi", "int", "all"]

    def __repr__(self) -> str:
        return f"<class Hero id={self.id} name={self.name}>"


def fill_hero_list() -> dict[int, Hero]:
    endpoint = "https://api.opendota.com/api/constants/heroes"
    response = requests.get(endpoint, timeout=15)
    data: dict[str, OpendotaConstantsHero] = response.json()

    return {
        hero["id"]: Hero(
            id=hero["id"],
            name=hero["localized_name"],
            npc_name=hero["name"],
            icon=f"https://cdn.cloudflare.steamstatic.com/{hero['img']}",
            primary_attribute=hero["primary_attr"],
        )
        for _, hero in data.items()
    }


heroes = fill_hero_list()
