"""Press "Refresh challenges" for every hero's Dota Plus quests.

Open any hero's loadout page in Dota 2 and start the script; it clicks through all heroes.
"""

from __future__ import annotations

import time
from typing import NamedTuple

from dota2utils_common import datafeed
from dota2utils_common.logs import logger, setup_logging

# Button positions measured on a 2560x1440 screen; scaled for other resolutions.
# The Dota 2 UI scales with screen height, so this works best on 16:9 screens.
BASE_RESOLUTION = (2560, 1440)


class Point(NamedTuple):
    x: float
    y: float


PROGRESS_TAB = Point(980, 112)
REFRESH_BUTTON = Point(830, 1130)
NEXT_HERO = Point(2430, 110)

START_DELAY = 2.0  # time to alt-tab into Dota 2;


def scale(point: Point, screen: tuple[int, int], base: tuple[int, int] = BASE_RESOLUTION) -> Point:
    """Convert a point measured on the `base` resolution to the `screen` resolution."""
    return Point(round(point.x * screen[0] / base[0]), round(point.y * screen[1] / base[1]))


def main() -> None:
    """Click "Refresh challenges" and "Next hero" once per hero."""
    setup_logging()
    # Imported here: pyautogui needs a display as soon as it's imported;
    import pyautogui  # ruff: ignore[import-outside-top-level]

    def click(point: Point, sleep_after: float = 0, *, repeat: int = 1) -> None:
        # Separate move/down/up with tiny pauses - instant clicks sometimes don't register in Dota 2;
        for _ in range(repeat):
            pyautogui.moveTo(point.x, point.y)
            time.sleep(0.001)
            pyautogui.mouseDown(button="left")
            time.sleep(0.001)
            pyautogui.mouseUp(button="left")
            time.sleep(0.05)
        time.sleep(sleep_after)

    screen = pyautogui.size()
    screen_size = (screen.width, screen.height)
    progress_tab, refresh_button, next_hero = (scale(p, screen_size) for p in (PROGRESS_TAB, REFRESH_BUTTON, NEXT_HERO))
    heroes_total = len(datafeed.get_heroes())

    logger.info(
        "👆 Clicking through {} heroes in {}s. Move the mouse to a screen corner to abort.", heroes_total, START_DELAY
    )
    time.sleep(START_DELAY)

    click(progress_tab, repeat=3)
    for _ in range(heroes_total):
        click(refresh_button, 0.15, repeat=3)
        click(next_hero, 0.15)
        time.sleep(0.3)

    logger.success("🎯 Refreshed quests for {} heroes.", heroes_total)
