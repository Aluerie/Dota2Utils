from __future__ import annotations

import json
import logging
import math
import pathlib
import shutil
from typing import TYPE_CHECKING, NamedTuple, TypedDict, override

from config import DOTA_FRIEND_ID
from utils import api

if TYPE_CHECKING:

    class HeroGridConfigJson(TypedDict):
        version: int
        configs: list[Config]

    class Config(TypedDict):
        config_name: str
        categories: list[Category]

    class Category(TypedDict):
        category_name: str
        x_position: float
        y_position: float
        width: float
        height: float
        hero_ids: list[int]


class Position(NamedTuple):
    x: int | float  # X
    y: int | float  # Y
    w: int | float  # Width
    h: int | float  # Height


log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

STEAM_CFG_DIR = f"C:\\Program Files (x86)\\Steam\\userdata\\{DOTA_FRIEND_ID}\\570\\remote\\cfg"
HERO_GRID_JSON = f"{STEAM_CFG_DIR}\\hero_grid_config.json"

OUT_TEMP = "./.temp"

# Coordinates for Hero Grid
MAX_X, MAX_Y = 1200, 592


class HeroGridBase:
    def __init__(
        self,
        hero_grid_json: HeroGridConfigJson,
        config_index: int,
        new_positions: dict[str, Position],
    ) -> None:
        self.hero_grid_json: HeroGridConfigJson = hero_grid_json
        self.config_index: int = config_index
        self.new_positions: dict[str, Position] = new_positions

    def update_categories(self) -> None:
        for name, position in self.new_positions.items():
            log.debug("Attempting to assign new positions for %s", name)
            for category in self.hero_grid_json["configs"][self.config_index]["categories"]:
                if category["category_name"] == name:
                    # Since self.hero_grid_json is mutable, it will change the original dict;
                    category["x_position"] = position.x
                    category["y_position"] = position.y
                    category["width"] = position.w
                    category["height"] = position.h
                    break
            else:
                msg = (
                    f'Category with name "{name}" does not exist in this hero grid.'
                    "Please add this category into your actual grid in Dota 2 client or in file yourself."
                )
                raise KeyError(msg)


class DotaPlusGrid(HeroGridBase):
    def __init__(self, hero_grid_json: HeroGridConfigJson) -> None:
        # CUSTOMIZE THESE VALUES

        # Changeable variables for categories
        sep = 450  # the "line" between my left and right grid parts;
        right_w = MAX_X - sep  # width of the right part;
        h = 100  # height, height of every "normal" category;
        d = 12  # delta, space between "normal" categories;

        bronze_delta = 10
        bronze5_h = 100

        super().__init__(
            hero_grid_json=hero_grid_json,
            config_index=1,
            new_positions={  # match these names with the ones you have in the hero grid
                "Grandmaster": Position(0, 0, sep / 2, h),
                "Master": Position(sep / 2, 0, sep / 2, h),
                "Platinum": Position(0, h + d, sep, h),
                "Gold": Position(0, 2 * (h + d), sep, h),
                "Silver": Position(0, 3 * (h + d), sep, MAX_Y - 3 * (h + d)),
                "Bronze 5, 475<=Xp": Position(sep, 0, right_w / 3, bronze5_h),
                "Bronze 5, 300<=Xp<475": Position(sep + right_w / 3, 0, right_w / 3, bronze5_h),
                "Bronze 5, XP<300": Position(sep + right_w * 2 / 3, 0, right_w / 3, bronze5_h),
                "Bronze 4-": Position(sep, bronze_delta + bronze5_h, right_w, MAX_Y - bronze_delta - bronze5_h),
            },
        )

    def sort_by_dota_plus_xp(self) -> None:
        """

        TODO
        ----
        I don't know how to do it.

        This Stratz API request can help, but it doesn't show
        * Heroes with levels below 11;
        * Exact XP number;

        ```
            query PlusLevels {
                player(steamAccountId: XXX) {
                    dotaPlus {
                        heroId
                        level
                    }
                }
            }
        ```
        """
        raise NotImplementedError


class DefaultRolesGrid(HeroGridBase):
    def __init__(self, hero_grid_json: HeroGridConfigJson) -> None:
        sep = 500  # the "line" between my left and right grid parts;
        self.sep = sep

        # POSITIONS
        height = 95
        rows = 5  # 5 positions in dota
        ban_space = 12

        # LAST ROW DETAILS
        last_row_h = 69
        last_row_w_ratio = 3 / 9
        turbo_bans_w = math.ceil(last_row_w_ratio * sep)  # if it's not an integer then it might bug out with 1 pixel lines

        # DELTA BETWEEN POSITIONS
        delta_pos = (MAX_Y - height * rows - last_row_h - ban_space) / (rows - 1)

        super().__init__(
            hero_grid_json,
            config_index=0,
            new_positions=(
                {f"pos{i + 1}": Position(0, (height + delta_pos) * i, sep, height) for i in range(rows)}
                | {
                    "Turbo bans": Position(0, MAX_Y - last_row_h, turbo_bans_w, last_row_h),
                    "Grind/Arcana/Style/D+/Etc": Position(turbo_bans_w, MAX_Y - last_row_h, sep - turbo_bans_w, last_row_h),
                }
            ),
        )

    def fix_attribute_categories(self) -> None:
        indexes = {"str": 5, "agi": 6, "int": 7, "all": -1}

        all_hero_ids: list[int] = []

        for count, (primary_attribute, idx) in enumerate(indexes.items()):
            category = self.hero_grid_json["configs"][self.config_index]["categories"][idx]

            category["x_position"] = self.sep
            category["y_position"] = count * MAX_Y / 4
            category["width"] = MAX_X - self.sep
            category["height"] = MAX_Y / 4

            # Fix alphabet if needed.
            category["hero_ids"] = sorted(category["hero_ids"], key=lambda x: api.heroes[x].name.casefold())

            # Print attribute warning mismatch.
            for hero_id in category["hero_ids"]:
                hero = api.heroes[hero_id]
                if primary_attribute != hero.primary_attribute:
                    log.warning("Primary Attribute mismatch for %s", hero)

            # Check if all heroes are present and not duplicated.
            all_hero_ids += category["hero_ids"]

        # Check for duplicates within attributes half of the screen.
        seen: set[int] = set()
        dupes = {x for x in all_hero_ids if x in seen or seen.add(x)}
        if dupes:
            log.warning("Duplicates found! %s", dupes)

        # Check for missing heroes within attributes half of the screen.
        missing_ids = set(api.heroes.keys()) - set(all_hero_ids)
        if missing_ids:
            missing_heroes = f"{[api.heroes[hero_id] for hero_id in missing_ids]}"
            log.warning("Missing heroes are found! %s", missing_heroes)

    @override
    def update_categories(self) -> None:
        self.fix_attribute_categories()
        super().update_categories()


def prepare_backup() -> None:
    """Copy the hero grid and create a backup."""
    if not pathlib.Path(OUT_TEMP).is_dir():
        pathlib.Path(OUT_TEMP).mkdir()

    # copy hero grid - we will work in it
    shutil.copy2(HERO_GRID_JSON, OUT_TEMP)
    # back up hero grid
    shutil.copy2(HERO_GRID_JSON, f"{OUT_TEMP}/backup.json")


def write_and_copy(hero_grid_json: HeroGridConfigJson) -> None:
    # WRITE INTO DUMP FILE
    with pathlib.Path(".temp/hero_grid_config.json").open("w", encoding="utf-8") as f:
        json.dump(hero_grid_json, f, ensure_ascii=False, indent=4)

    # COPY DUMP FILE BACK TO STEAM_CFG_LOC FOLDER WHEN WE ARE DONE
    shutil.copy2(f"{OUT_TEMP}/hero_grid_config.json", STEAM_CFG_DIR)


def main() -> None:
    """Sort my Dota Plus Hero Levels Grids."""
    log.info("Starting")
    prepare_backup()

    with pathlib.Path(".temp/hero_grid_config.json").open(encoding="utf-8") as json_file:
        hero_grid_json: HeroGridConfigJson = json.load(json_file)

    DotaPlusGrid(hero_grid_json).update_categories()
    DefaultRolesGrid(hero_grid_json).update_categories()

    write_and_copy(hero_grid_json)


if __name__ == "__main__":
    main()
