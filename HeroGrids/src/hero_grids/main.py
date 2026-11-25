"""Align the categories of my Dota 2 hero grids pixel-perfectly.

The layouts here are my personal arrangement; edit the `*_layout` functions and category names for yours.
"""

from __future__ import annotations

import copy
import datetime as dt
import json
import math
import pathlib
import shutil
from collections import Counter
from typing import TYPE_CHECKING, NamedTuple, TypedDict

from dota2utils_common import Dota2UtilsError, datafeed, steam
from dota2utils_common.logs import logger, setup_logging

if TYPE_CHECKING:
    from dota2utils_common.datafeed import Hero, PrimaryAttribute

    class HeroGridJson(TypedDict):
        version: int
        configs: list[GridConfig]

    class GridConfig(TypedDict):
        config_name: str
        categories: list[Category]

    class Category(TypedDict):
        category_name: str
        x_position: float
        y_position: float
        width: float
        height: float
        hero_ids: list[int]


# HeroGrids/src/hero_grids/main.py -> HeroGrids/.temp
BACKUP_DIR = pathlib.Path(__file__).resolve().parents[2] / ".temp" / "backups"
BACKUPS_TO_KEEP = 20

# Size of the hero grid canvas in the Dota 2 client;
MAX_X, MAX_Y = 1200, 592

# Names of the grids (`config_name` in the json) - match these with the ones in your Dota 2 client;
DOTA_PLUS_GRID = "DotaPlus levels"
ROLES_GRID = "(!) Look in Dota Plus Grid for roles"

ATTRIBUTE_ORDER: tuple[PrimaryAttribute, ...] = ("str", "agi", "int", "all")


class Box(NamedTuple):
    """A rectangle mirroring a category in Dota 2 hero grids (stored as X-Y-W-H in the json file)."""

    x: float
    y: float
    w: float
    h: float

    def overlaps(self, other: Box) -> bool:
        return (
            self.x < other.x + other.w
            and other.x < self.x + self.w
            and self.y < other.y + other.h
            and other.y < self.y + self.h
        )


def dota_plus_layout() -> dict[str, Box]:
    """Category name -> box for the Dota Plus levels grid.

    Idea: sort heroes by Dota Plus XP automatically. Stratz API (`player.dotaPlus { heroId level }`) has levels,
    but not for heroes below level 11 and not the exact XP numbers.
    """
    sep = 450  # the "line" between the left and right parts;
    right_w = MAX_X - sep  # width of the right part;
    h = 100  # height of every "normal" category;
    d = 12  # space between "normal" categories;

    bronze_delta = 10
    bronze5_h = 100

    return {
        "Grandmaster": Box(0, 0, sep / 2, h),
        "Master": Box(sep / 2, 0, sep / 2, h),
        "Platinum": Box(0, h + d, sep, h),
        "Gold": Box(0, 2 * (h + d), sep, h),
        "Silver": Box(0, 3 * (h + d), sep, MAX_Y - 3 * (h + d)),
        "Bronze 5, 475<=Xp": Box(sep, 0, right_w / 3, bronze5_h),
        "Bronze 5, 300<=Xp<475": Box(sep + right_w / 3, 0, right_w / 3, bronze5_h),
        "Bronze 5, XP<300": Box(sep + right_w * 2 / 3, 0, right_w / 3, bronze5_h),
        "Bronze 4-": Box(sep, bronze_delta + bronze5_h, right_w, MAX_Y - bronze_delta - bronze5_h),
    }


# The "line" between the positions (left) and attributes (right) parts of the roles grid;
ROLES_SEP = 500


def roles_layout() -> dict[str, Box]:
    """Category name -> box for the left part of the roles grid."""
    sep = ROLES_SEP

    # Positions
    pos_box_height = 95
    total_positions = 5

    # Extra row (Turbo bans, some event grind)
    last_row_y_extra_space = 12
    last_row_box_height = 69
    turbo_bans_box_width = math.ceil(3 / 9 * sep)  # if it's not an integer then it might bug out with 1 pixel lines

    delta_y_between_pos = int(
        (MAX_Y - pos_box_height * total_positions - last_row_box_height - last_row_y_extra_space) / (total_positions - 1)
    )
    row_step = pos_box_height + delta_y_between_pos

    # Arcana grind sits to the right of pos2-pos5
    arcana_y = int(row_step + 15)
    pos_2_till_5_width = int(1 / 2 * sep - 20)
    arcana_x = pos_2_till_5_width

    return {
        "pos1": Box(0, 0, sep, pos_box_height),
        "pos2": Box(0, row_step * 1, pos_2_till_5_width, pos_box_height),
        "pos3": Box(0, row_step * 2, pos_2_till_5_width, pos_box_height),
        "pos4": Box(0, row_step * 3, pos_2_till_5_width, pos_box_height),
        "pos5": Box(0, row_step * 4, pos_2_till_5_width, pos_box_height),
        "Turbo bans": Box(0, MAX_Y - last_row_box_height, turbo_bans_box_width, last_row_box_height),
        "Arcana Grind": Box(arcana_x, arcana_y, sep - arcana_x, MAX_Y - arcana_y - 1),
    }


def attribute_layout() -> dict[PrimaryAttribute, Box]:
    """Primary attribute -> box for the right part of the roles grid: four rows, str/agi/int/universal."""
    box_height = MAX_Y / 4
    return {
        attribute: Box(ROLES_SEP, count * box_height, MAX_X - ROLES_SEP, box_height)
        for count, attribute in enumerate(ATTRIBUTE_ORDER)
    }


def find_config(grid: HeroGridJson, name: str) -> GridConfig:
    """Find a grid by its name (ignoring surrounding whitespace)."""
    for config in grid["configs"]:
        if config["config_name"].strip() == name.strip():
            return config
    names = ", ".join(f'"{c["config_name"]}"' for c in grid["configs"])
    msg = f'Hero grid "{name}" not found. Grids in your client: {names}.'
    raise Dota2UtilsError(msg)


def place(category: Category, box: Box) -> None:
    category["x_position"] = box.x
    category["y_position"] = box.y
    category["width"] = box.w
    category["height"] = box.h


def apply_layout(config: GridConfig, layout: dict[str, Box]) -> None:
    """Move and resize the grid's categories by name."""
    categories = {category["category_name"]: category for category in config["categories"]}
    for name, box in layout.items():
        if name not in categories:
            msg = f'Category "{name}" does not exist in hero grid "{config["config_name"]}". Add it in the Dota 2 client.'
            raise Dota2UtilsError(msg)
        place(categories[name], box)


def find_attribute_categories(config: GridConfig, heroes: dict[int, Hero]) -> dict[PrimaryAttribute, Category]:
    """Find the unnamed str/agi/int/universal categories by the primary attribute most of their heroes have."""
    found: dict[PrimaryAttribute, Category] = {}
    for category in config["categories"]:
        if category["category_name"]:
            continue
        attributes = Counter(heroes[hero_id].primary_attribute for hero_id in category["hero_ids"] if hero_id in heroes)
        if not attributes:
            continue
        attribute = attributes.most_common(1)[0][0]
        if attribute in found:
            msg = f'Two unnamed categories in "{config["config_name"]}" are mostly "{attribute}" heroes.'
            raise Dota2UtilsError(msg)
        found[attribute] = category

    if missing := [attribute for attribute in ATTRIBUTE_ORDER if attribute not in found]:
        msg = f'Could not find unnamed categories for {missing} heroes in hero grid "{config["config_name"]}".'
        raise Dota2UtilsError(msg)
    return found


def fix_attribute_categories(config: GridConfig, heroes: dict[int, Hero]) -> None:
    """Lay out the attribute categories and keep them correct.

    Heroes whose primary attribute changed (i.e. in a patch) are moved to the right category,
    heroes missing from all of them (i.e. new heroes) are added, and every category is sorted alphabetically.
    """
    categories = find_attribute_categories(config, heroes)

    # Move heroes that are in the wrong attribute category;
    for attribute, category in categories.items():
        for hero_id in list(category["hero_ids"]):
            hero = heroes.get(hero_id)
            if hero is not None and hero.primary_attribute != attribute:
                category["hero_ids"].remove(hero_id)
                categories[hero.primary_attribute]["hero_ids"].append(hero_id)
                logger.info("🔀 Moved {} from the {} to the {} category", hero, attribute, hero.primary_attribute)

    # Add heroes that are in none of them;
    all_hero_ids = [hero_id for category in categories.values() for hero_id in category["hero_ids"]]
    for hero_id in sorted(heroes.keys() - set(all_hero_ids)):
        hero = heroes[hero_id]
        categories[hero.primary_attribute]["hero_ids"].append(hero_id)
        logger.info("🆕 Added {} to the {} category", hero, hero.primary_attribute)

    if duplicates := {hero_id for hero_id, count in Counter(all_hero_ids).items() if count > 1}:
        logger.warning("👯 Heroes in more than one attribute category: {}", [str(heroes.get(i, i)) for i in duplicates])

    layout = attribute_layout()
    for attribute, category in categories.items():
        place(category, layout[attribute])
        known_ids = [hero_id for hero_id in category["hero_ids"] if hero_id in heroes]
        unknown_ids = [hero_id for hero_id in category["hero_ids"] if hero_id not in heroes]
        if unknown_ids:
            logger.warning("❓ Hero IDs not in the dota2.com hero list (kept at the end): {}", unknown_ids)
        category["hero_ids"] = sorted(known_ids, key=lambda hero_id: heroes[hero_id].localized_name.casefold()) + unknown_ids


def update_grid(grid: HeroGridJson, heroes: dict[int, Hero]) -> None:
    """Apply all my layouts to the hero grid json (in place)."""
    apply_layout(find_config(grid, DOTA_PLUS_GRID), dota_plus_layout())

    roles = find_config(grid, ROLES_GRID)
    fix_attribute_categories(roles, heroes)
    apply_layout(roles, roles_layout())


def backup(path: pathlib.Path) -> pathlib.Path:
    """Copy the hero grid file to a timestamped backup, so a bad run never overwrites the last good one."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now().astimezone().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = BACKUP_DIR / f"hero_grid_config_{timestamp}.json"
    shutil.copy2(path, backup_path)
    return backup_path


def prune_backups(keep: int = BACKUPS_TO_KEEP) -> list[pathlib.Path]:
    """Delete all but the `keep` newest backups; returns the deleted files."""
    # Names are `hero_grid_config_<YYYY-MM-DD_HH-MM-SS>.json`, so sorting by name sorts by time;
    backups = sorted(BACKUP_DIR.glob("hero_grid_config_*.json"))
    old = backups[:-keep] if keep > 0 else backups
    for path in old:
        path.unlink()
    return old


def run() -> None:
    """Re-align the grids in the Dota 2 client's `hero_grid_config.json`, backing it up first.

    Does nothing (no backup, no write) if the grids are already as they should be.
    """
    path = steam.cfg_dir() / "hero_grid_config.json"
    if not path.is_file():
        msg = f"Hero grid file not found: {path}. Save a hero grid in the Dota 2 client once."
        raise Dota2UtilsError(msg)

    with path.open(encoding="utf-8") as f:
        grid: HeroGridJson = json.load(f)
    original = copy.deepcopy(grid)

    update_grid(grid, datafeed.get_heroes())

    # Compares values, so `148` in the file and `148.0` from the layout math count as equal;
    if grid == original:
        logger.success("✨ Hero grids are already up to date - nothing to do.")
        return

    logger.info("💾 Backed up the current hero grid to {}", backup(path))
    if pruned := prune_backups():
        logger.info("🧹 Deleted {} old backup(s), keeping the {} newest", len(pruned), BACKUPS_TO_KEEP)

    with path.open("w", encoding="utf-8") as f:
        json.dump(grid, f, ensure_ascii=False, indent=4)
    logger.success("📐 Updated the hero grids in {}", path)


def main() -> None:
    """Re-align my hero grids, printing problems as plain messages."""
    setup_logging()
    try:
        run()
    except Dota2UtilsError as exc:
        logger.error(str(exc))
        raise SystemExit(1) from exc
