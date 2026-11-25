from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from dota2utils_common import datafeed

if TYPE_CHECKING:
    from collections.abc import Iterator

HEROLIST = {
    "heroes": [
        {
            "id": 1,
            "name": "npc_dota_hero_antimage",
            "name_loc": "Anti-Mage",
            "name_english_loc": "Anti-Mage",
            "primary_attr": 1,
        },
        {
            "id": 5,
            "name": "npc_dota_hero_crystal_maiden",
            "name_loc": "CM",
            "name_english_loc": "Crystal Maiden",
            "primary_attr": 2,
        },
        {"id": 120, "name": "npc_dota_hero_pangolier", "name_loc": "P", "name_english_loc": "Pangolier", "primary_attr": 3},
    ],
}
ITEMLIST = {"itemabilities": [{"id": 1, "name": "item_blink"}, {"id": 36, "name": "item_magic_wand"}]}


@pytest.fixture(autouse=True)
def fake_datafeed(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    responses: dict[str, Any] = {"herolist": HEROLIST, "itemlist": ITEMLIST}
    monkeypatch.setattr(datafeed, "_get", lambda endpoint: responses[endpoint])
    datafeed.get_heroes.cache_clear()
    datafeed.get_item_names.cache_clear()
    yield
    datafeed.get_heroes.cache_clear()
    datafeed.get_item_names.cache_clear()


def test_get_heroes() -> None:
    heroes = datafeed.get_heroes()
    assert set(heroes) == {1, 5, 120}
    cm = heroes[5]
    assert (str(cm), cm.slug_name, cm.primary_attribute) == ("Crystal Maiden", "crystal_maiden", "int")
    assert heroes[1].primary_attribute == "agi"
    assert heroes[120].primary_attribute == "all"


def test_get_item_names() -> None:
    assert datafeed.get_item_names() == {1: "item_blink", 36: "item_magic_wand"}
