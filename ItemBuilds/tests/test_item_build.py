from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import pytest
import vdf
from steam.ext.dota2 import Hero

from dota2utils_common import ConfigError, guides
from item_builds import item_build, main, stratz
from item_builds.const import Role

if TYPE_CHECKING:
    import pathlib

ITEM_NAMES = {
    1: "item_blink",
    29: "item_boots",
    36: "item_magic_wand",
    41: "item_bottle",
    63: "item_power_treads",
    116: "item_black_king_bar",
    147: "item_manta",
    244: "item_wind_lace",
}


def overview_row(item_id: int, purchase_rate: float, avg_minute: float = 30.0) -> dict[str, Any]:
    return {"item_id": item_id, "hero_purchase_rate": purchase_rate, "best_order": {"avg_minute": avg_minute}}


def overview(*rows: dict[str, Any]) -> Any:
    return {"overviewRows": list(rows), "recommendedItems": [], "period": "full"}


def matches(*item_lists: list[int]) -> Any:
    return [{"data": {"items": [{"item_id": i} for i in items]}} for items in item_lists]


def test_categorize_items_by_purchase_rate() -> None:
    categories = item_build.categorize_items(
        overview(
            overview_row(63, 0.60, avg_minute=12.0),  # popular and early -> Early
            overview_row(116, 0.55),  # popular and late -> Meta
            overview_row(147, 0.04),  # 1.3%..5% -> Low Percent
            overview_row(1, 0.005),  # below 1.3% -> ignored
            overview_row(29, 0.90, avg_minute=5.0),  # boots are already in Early -> not duplicated
        ),
        early_match_items=[41],
        role=Role.Carry,
        item_names=ITEM_NAMES,
        my_additions=["item_rapier"],
    )
    assert list(categories) == ["Consumables", "Early", "Meta: Carry", "Low Percent (<5%)", "My additions"]
    assert categories["Early"] == ["item_boots", "item_power_treads", "item_bottle"]
    assert categories["Meta: Carry"] == ["item_black_king_bar"]
    assert categories["Low Percent (<5%)"] == ["item_manta"]
    assert categories["My additions"] == ["item_rapier"]


def test_unknown_items_are_skipped() -> None:
    categories = item_build.categorize_items(overview(overview_row(9999, 0.5)), [], Role.Mid, ITEM_NAMES, [])
    assert categories["Meta: Mid"] == []


def test_match_items_counted_once_per_match() -> None:
    hero_matches = matches(
        [36, 36, 36],  # three wands in one match still count once
        [41],
        [41],
        [],
        [],
        [],
    )
    assert item_build.common_match_items(hero_matches) == [41]  # bottle 2/6 = 33%, wand 1/6 = 17% (< 20%)
    assert item_build.common_match_items([]) == []


def test_write_categories_keeps_my_additions(tmp_path: pathlib.Path) -> None:
    guide = guides.new_guide("lina", friend_id=1, gameplay_version="7.41e")
    item_build.write_categories(guide, {"My additions": ["item_blink", "item_blink"]}, "7.41e")
    path = tmp_path / "lina_1.build"
    guides.save_guide(guide, path)

    loaded = guides.load_guide(path)
    assert str(loaded["guidedata"]["Title"]).endswith("; 7.41e")
    assert item_build.saved_additions(loaded) == ["item_blink", "item_blink"]
    assert item_build.saved_additions(vdf.VDFDict([("guidedata", vdf.VDFDict())])) == []


def test_load_hero_roles(isolated_config: pathlib.Path) -> None:
    isolated_config.write_text('[item_builds.heroes]\nDrowRanger = "Carry"\nChen = "HardSupport"\n', encoding="utf-8")
    assert {(hero.name, role) for hero, role in main.load_hero_roles().items()} == {
        ("DrowRanger", Role.Carry),
        ("Chen", Role.HardSupport),
    }


@pytest.mark.parametrize(
    ("heroes", "error"),
    [
        ("", "Add the heroes"),
        ('NotAHero = "Carry"', "Unknown hero `NotAHero`"),
        ('Chen = "Jungle"', "Unknown role `Jungle`"),
    ],
)
def test_load_hero_roles_errors(isolated_config: pathlib.Path, heroes: str, error: str) -> None:
    isolated_config.write_text(f"[item_builds.heroes]\n{heroes}\n", encoding="utf-8")
    with pytest.raises(ConfigError, match=error):
        main.load_hero_roles()


def test_common_shared_items() -> None:
    shares = {36: 0.63, 75: 0.51, 41: 0.05, 73: 0.2, 1: 0.9}  # blink (1) is not one of the match items
    assert item_build.common_shared_items(shares) == [36, 75, 73]


def test_stratz_purchase_shares() -> None:
    data = {
        "heroStats": {
            "stats": [{"matchCount": 1000}],
            "itemFullPurchase": [
                {"itemId": 36, "matchCount": 400},  # split by game minute - summed up
                {"itemId": 36, "matchCount": 230},
                {"itemId": 75, "matchCount": 1500},  # purchases, not matches - capped at 100%
            ],
        },
    }
    assert stratz.purchase_shares(data) == {36: 0.63, 75: 1.0}
    assert stratz.purchase_shares({"heroStats": {"stats": [{"matchCount": 50}], "itemFullPurchase": []}}) == {}
    assert stratz.purchase_shares({"heroStats": {"stats": None, "itemFullPurchase": None}}) == {}


class FakeD2PT:
    def __init__(self, matches: Any = None, error: Exception | None = None) -> None:
        self.matches, self.error = matches, error

    async def hero_matches(self, _hero: Any, _role: Any) -> Any:
        if self.error:
            raise self.error
        return self.matches


class FakeStratz:
    def __init__(self, shares: dict[int, float] | None = None, error: Exception | None = None) -> None:
        self.shares, self.error, self.calls = shares or {}, error, 0

    async def item_purchase_shares(self, _hero_id: int, _position: int) -> dict[int, float]:
        self.calls += 1
        if self.error:
            raise self.error
        return self.shares


def early_items(d2pt: FakeD2PT, stratz: FakeStratz | None) -> list[int]:
    return asyncio.run(main.early_match_items(Hero.DrowRanger, Role.Carry, d2pt, stratz))  # ty: ignore[invalid-argument-type]


FORBIDDEN = RuntimeError('{"message": "Forbidden"}')


def test_early_items_from_d2pt_matches() -> None:
    stratz_client = FakeStratz({36: 0.9})
    assert early_items(FakeD2PT(matches([41], [41], [])), stratz_client) == [41]
    assert stratz_client.calls == 0  # D2PT worked - no need for Stratz


def test_early_items_fall_back_to_stratz() -> None:
    assert early_items(FakeD2PT(error=FORBIDDEN), FakeStratz({36: 0.63, 75: 0.1})) == [36]
    assert early_items(FakeD2PT(matches=[]), FakeStratz({36: 0.63})) == [36]  # no matches - Stratz too


def test_early_items_skipped_when_both_fail() -> None:
    assert early_items(FakeD2PT(error=FORBIDDEN), None) == []  # no token
    assert early_items(FakeD2PT(error=FORBIDDEN), FakeStratz(error=TimeoutError())) == []
    assert early_items(FakeD2PT(error=FORBIDDEN), FakeStratz({})) == []  # Stratz has no data


def test_describe_changes() -> None:
    guide = guides.new_guide("lina", friend_id=1, gameplay_version="7.41e")
    item_build.write_categories(guide, {"Early": ["item_boots", "item_bracer"], "Old": ["item_blink"]}, "7.41e")
    old = item_build.current_categories(guide)
    assert old == {"Early": ["item_boots", "item_bracer"], "Old": ["item_blink"]}

    new = {"Early": ["item_boots", "item_magic_wand"], "Meta: Mid": ["item_manta"]}
    assert item_build.describe_changes(old, new) == [
        "Early: +magic_wand -bracer",
        "Meta: Mid: +manta",
        "Old: -blink",
    ]
    assert item_build.describe_changes(new, new) == []
    assert item_build.current_categories(vdf.VDFDict([("guidedata", vdf.VDFDict())])) == {}


class FakeOverviewD2PT(FakeD2PT):
    @staticmethod
    async def item_overview(_hero: Any, _role: Any) -> Any:
        return overview(overview_row(116, 0.5))  # BKB in the "Meta" category


@pytest.mark.parametrize("dry_run", [True, False])
def test_dry_run_writes_nothing(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, *, dry_run: bool) -> None:
    monkeypatch.setattr(main.steam, "guides_dir", lambda: tmp_path)
    guide = guides.new_guide("lina", friend_id=1, gameplay_version="7.41e")
    path = tmp_path / "lina_1.build"
    guides.save_guide(guide, path)
    before = path.read_bytes()

    run: Any = main.Run(
        d2pt=FakeOverviewD2PT(matches([])),  # ty: ignore[invalid-argument-type]
        stratz=None,
        gameplay_version="7.41e",
        item_names=ITEM_NAMES,
        dry_run=dry_run,
    )
    asyncio.run(main.process_hero(Hero.Lina, Role.Mid, run))

    if dry_run:
        assert path.read_bytes() == before
    else:
        assert "item_black_king_bar" in item_build.current_categories(guides.load_guide(path))["Meta: Mid"]
