from __future__ import annotations

import itertools
import json
from typing import TYPE_CHECKING, Any

import pytest

from dota2utils_common import Dota2UtilsError
from dota2utils_common.datafeed import Hero
from hero_grids import main

if TYPE_CHECKING:
    import pathlib

    from hero_grids.main import Box

HEROES = {
    1: Hero(1, "npc_dota_hero_antimage", "Anti-Mage", "agi"),
    2: Hero(2, "npc_dota_hero_axe", "Axe", "str"),
    5: Hero(5, "npc_dota_hero_crystal_maiden", "Crystal Maiden", "int"),
    14: Hero(14, "npc_dota_hero_pudge", "Pudge", "str"),
    26: Hero(26, "npc_dota_hero_lion", "Lion", "int"),
    120: Hero(120, "npc_dota_hero_pangolier", "Pangolier", "all"),
    136: Hero(136, "npc_dota_hero_marci", "Marci", "all"),
}


def assert_valid_layout(boxes: list[Box]) -> None:
    for box in boxes:
        assert box.x >= 0
        assert box.y >= 0
        assert box.x + box.w <= main.MAX_X
        assert box.y + box.h <= main.MAX_Y
    for a, b in itertools.combinations(boxes, 2):
        assert not a.overlaps(b), (a, b)


def test_dota_plus_layout() -> None:
    assert_valid_layout(list(main.dota_plus_layout().values()))


def test_roles_layout_and_attributes_fit_together() -> None:
    assert_valid_layout([*main.roles_layout().values(), *main.attribute_layout().values()])


def category(name: str, hero_ids: list[int]) -> dict[str, Any]:
    return {"category_name": name, "x_position": 0, "y_position": 0, "width": 1, "height": 1, "hero_ids": hero_ids}


def roles_grid(*categories: dict[str, Any]) -> Any:
    return {"config_name": "(!) Look in Dota Plus Grid for roles ", "categories": list(categories)}


def test_attribute_categories_found_by_heroes() -> None:
    config = roles_grid(
        category("pos1", [1]),
        category("", [120]),
        category("", [5]),
        category("", [14, 2, 1]),  # mostly str, Anti-Mage misplaced
        category("", []),  # empty unnamed categories are ignored
        category("", [1]),
    )
    main.fix_attribute_categories(config, HEROES)

    str_category = config["categories"][3]
    assert str_category["hero_ids"] == [2, 14]  # misplaced Anti-Mage moved out; sorted: Axe, Pudge
    assert (str_category["x_position"], str_category["y_position"]) == (main.ROLES_SEP, 0)
    assert config["categories"][1]["y_position"] == main.MAX_Y * 3 / 4  # universal is the last row


def test_misplaced_and_missing_heroes_are_fixed() -> None:
    config = roles_grid(
        category("", [2, 14, 120]),  # mostly str; Pangolier is universal now (like Meepo)
        category("", [1]),
        category("", [26]),  # Crystal Maiden is missing everywhere (like a new hero)
        category("", [999, 136]),  # unknown ID: kept, at the end
    )
    main.fix_attribute_categories(config, HEROES)

    str_, agi, int_, universal = (c["hero_ids"] for c in config["categories"])
    assert str_ == [2, 14]
    assert agi == [1]
    assert int_ == [5, 26]  # Crystal Maiden added; sorted before Lion
    assert universal == [136, 120, 999]  # Pangolier moved in; Marci, Pangolier, then the unknown ID


def test_attribute_categories_missing() -> None:
    config = roles_grid(category("", [2]), category("", [1]))
    with pytest.raises(Dota2UtilsError, match="'int', 'all'"):
        main.fix_attribute_categories(config, HEROES)


def test_find_config_by_name_ignores_whitespace() -> None:
    grid: Any = {"version": 3, "configs": [{"config_name": "DotaPlus levels", "categories": []}, roles_grid()]}
    assert main.find_config(grid, main.ROLES_GRID) is grid["configs"][1]
    with pytest.raises(Dota2UtilsError, match='Grids in your client: "DotaPlus levels"'):
        main.find_config(grid, "Nope")


def test_apply_layout_requires_categories() -> None:
    config = roles_grid(category("pos1", []))
    with pytest.raises(Dota2UtilsError, match='Category "pos2"'):
        main.apply_layout(config, main.roles_layout())


@pytest.fixture
def grid_file(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> pathlib.Path:
    """A fake Steam `cfg` folder with a hero grid file that has all my grids and categories, not yet aligned."""
    monkeypatch.setattr(main.steam, "cfg_dir", lambda: tmp_path)
    monkeypatch.setattr(main.datafeed, "get_heroes", lambda: HEROES)
    monkeypatch.setattr(main, "BACKUP_DIR", tmp_path / "backups")
    grid = {
        "version": 3,
        "configs": [
            roles_grid(
                *(category(name, []) for name in main.roles_layout()),
                category("", [2, 14]),
                category("", [1]),
                category("", [5, 26]),
                category("", [120, 136]),
            ),
            {"config_name": main.DOTA_PLUS_GRID, "categories": [category(name, []) for name in main.dota_plus_layout()]},
        ],
    }
    path = tmp_path / "hero_grid_config.json"
    path.write_text(json.dumps(grid), encoding="utf-8")
    return path


def test_run_updates_then_skips_when_up_to_date(grid_file: pathlib.Path) -> None:
    main.run()
    updated = grid_file.read_text(encoding="utf-8")
    assert json.loads(updated)["configs"][1]["categories"][0]["width"] != 1  # aligned
    assert len(list(main.BACKUP_DIR.iterdir())) == 1

    main.run()  # nothing to change now
    assert grid_file.read_text(encoding="utf-8") == updated
    assert len(list(main.BACKUP_DIR.iterdir())) == 1  # no new backup


def test_prune_backups_keeps_newest(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "BACKUP_DIR", tmp_path)
    names = [f"hero_grid_config_2026-11-{day:02d}_12-00-00.json" for day in range(1, 6)]
    for name in names:
        (tmp_path / name).touch()
    (tmp_path / "notes.txt").touch()  # not a backup - left alone

    deleted = main.prune_backups(keep=2)

    assert sorted(p.name for p in deleted) == names[:3]
    assert sorted(p.name for p in tmp_path.iterdir()) == [*names[3:], "notes.txt"]
