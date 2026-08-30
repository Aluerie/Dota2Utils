from __future__ import annotations

import time
from typing import TYPE_CHECKING, TypedDict

import pyautogui
import requests

if TYPE_CHECKING:

    class ResolutionConst(TypedDict):
        refresh_button: tuple[int, int]
        progress_tab: tuple[int, int]
        next_hero: tuple[int, int]


RESOLUTION_MAPPING: dict[str, ResolutionConst] = {
    "1920_1080": {
        # Maybe outdated ?
        "progress_tab": (729, 88),
        "refresh_button": (610, 842),
        "next_hero": (1817, 86),
    },
    "2160_1440": {
        "progress_tab": (980, 112),
        "refresh_button": (830, 1130),
        "next_hero": (2430, 110),
    },
}


def mouse_left_click(
    xy: tuple[float, float],
    sleep_after: float = 0,
    *,
    repeat: int = 1,
    sleep_between_repeats: float = 0.05,
) -> None:
    for _ in range(repeat):
        pyautogui.moveTo(xy)
        time.sleep(0.001)
        pyautogui.mouseDown(xy, button="left")
        time.sleep(0.001)
        pyautogui.mouseUp(xy, button="left")
        time.sleep(sleep_between_repeats)
    time.sleep(sleep_after)


def get_opendota_constants_heroes() -> list[str]:
    response = requests.get("https://api.opendota.com/api/constants/heroes", timeout=15)
    heroes_names_list = [v["localized_name"] for v in response.json().values()]
    return sorted(heroes_names_list)


def main() -> None:
    my_resolution = RESOLUTION_MAPPING["2160_1440"]
    heroes_total = len(get_opendota_constants_heroes())

    time.sleep(2.0)

    mouse_left_click(my_resolution["progress_tab"], repeat=3)
    for _ in range(heroes_total):
        mouse_left_click(my_resolution["refresh_button"], 0.15, repeat=3)
        mouse_left_click(my_resolution["next_hero"], 0.15)
        time.sleep(0.3)


if __name__ == "__main__":
    main()
