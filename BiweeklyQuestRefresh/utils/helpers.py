import pyautogui
import time

import requests


def mouse_left_click(
    xy: tuple[float, float],
    sleep_after: float = 0,
    *,
    repeat: int = 1,
    sleep_between_repeats: float = 0.05,
):
    for _ in range(repeat):
        pyautogui.moveTo(xy)
        time.sleep(0.001)
        pyautogui.mouseDown(xy, button="left")
        time.sleep(0.001)
        pyautogui.mouseUp(xy, button="left")
        time.sleep(sleep_between_repeats)
    time.sleep(sleep_after)


def get_opendota_constants_heroes() -> list[str]:
    response = requests.get("https://api.opendota.com/api/constants/heroes")
    heroes_names_list = [v["localized_name"] for v in response.json().values()]
    return sorted(heroes_names_list)


def is_turbo_quest_located(region: tuple[int, int, int, int]) -> bool:
    item_images = ["item_soul_ring.png", "item_midas.png"]
    for item in item_images:
        if pyautogui.locateOnScreen(f"./images/{item}", confidence=0.9, region=region):
            return True

    return False
