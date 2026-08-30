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


class Box(NamedTuple):
    """Just a rectangle mirroring a category in Dota 2 Hero Grids.

    In the json file they stored as X-Y-W-H rectangles so we mirror that.
    """

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
        new_positions: dict[str, Box],
    ) -> None:
        self.hero_grid_json: HeroGridConfigJson = hero_grid_json
        self.config_index: int = config_index
        self.new_positions: dict[str, Box] = new_positions

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
                "Grandmaster": Box(0, 0, sep / 2, h),
                "Master": Box(sep / 2, 0, sep / 2, h),
                "Platinum": Box(0, h + d, sep, h),
                "Gold": Box(0, 2 * (h + d), sep, h),
                "Silver": Box(0, 3 * (h + d), sep, MAX_Y - 3 * (h + d)),
                "Bronze 5, 475<=Xp": Box(sep, 0, right_w / 3, bronze5_h),
                "Bronze 5, 300<=Xp<475": Box(sep + right_w / 3, 0, right_w / 3, bronze5_h),
                "Bronze 5, XP<300": Box(sep + right_w * 2 / 3, 0, right_w / 3, bronze5_h),
                "Bronze 4-": Box(sep, bronze_delta + bronze5_h, right_w, MAX_Y - bronze_delta - bronze5_h),
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
        pos_box_height = 95
        total_positions = 5  # 5 positions in dota

        # EXTRA ROW (Turbo bans, some event grind) DETAILS
        last_row_y_extra_space = 12
        last_row_box_height = 69
        turbo_bans_box_width = math.ceil(3 / 9 * sep)  # if it's not an integer then it might bug out with 1 pixel lines

        # DELTA BETWEEN POSITIONS
        delta_y_between_pos = int(
            (MAX_Y - pos_box_height * total_positions - last_row_box_height - last_row_y_extra_space) / (total_positions - 1)
        )

        # Arcana related stuff
        arcana_y = int((pos_box_height + delta_y_between_pos) + 15)
        pos_2_till_5_width = int(1 / 2 * sep - 20)
        arcana_x = pos_2_till_5_width

        super().__init__(
            hero_grid_json,
            config_index=0,
            new_positions={
                "pos1": Box(0, 0, sep, pos_box_height),
                "pos2": Box(0, (pos_box_height + delta_y_between_pos) * 1, pos_2_till_5_width, pos_box_height),
                "pos3": Box(0, (pos_box_height + delta_y_between_pos) * 2, pos_2_till_5_width, pos_box_height),
                "pos4": Box(0, (pos_box_height + delta_y_between_pos) * 3, pos_2_till_5_width, pos_box_height),
                "pos5": Box(0, (pos_box_height + delta_y_between_pos) * 4, pos_2_till_5_width, pos_box_height),
                "Turbo bans": Box(0, MAX_Y - last_row_box_height, turbo_bans_box_width, last_row_box_height),
                "Arcana Grind": Box(arcana_x, arcana_y, sep - arcana_x, MAX_Y - arcana_y - 1),
            },
        )

    def fix_attribute_categories(self) -> None:
        indexes = {"str": 5, "agi": 6, "int": 7, "all": -2}  # hardcoded indexes - uh oh

        all_hero_ids: list[int] = []

        for count, (primary_attribute, idx) in enumerate(indexes.items()):
            category = self.hero_grid_json["configs"][self.config_index]["categories"][idx]

            box_height = MAX_Y / 4
            category["x_position"] = self.sep
            category["width"] = MAX_X - self.sep
            category["y_position"] = count * box_height
            category["height"] = box_height

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
    log.info("Finished")


if __name__ == "__main__":
    main()
