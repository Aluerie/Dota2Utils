import logging as log
import sys

import pyautogui as pag
import time
import requests

targets = log.StreamHandler(sys.stdout), log.FileHandler("_quests_refresh.logs")
log.basicConfig(format="%(message)s", level=log.INFO, handlers=targets)

# 1920x1080 resolution
XY_progress = (729, 88)
XY_refresh = (610, 842)


def left_mouse_click(xy, wait_after: float = 0, *, repeat=1, wait_repeat: float = 0.05):
    for _ in range(repeat):
        pag.moveTo(xy)
        time.sleep(0.001)
        pag.mouseDown(xy, button="left")
        time.sleep(0.001)
        pag.mouseUp(xy, button="left")
        time.sleep(wait_repeat)
    time.sleep(wait_after)


def opendota_constants_heroes():
    endpoint = "https://api.opendota.com/api/constants/heroes"
    response = requests.get(endpoint)
    heroes_names_list = [v["localized_name"] for k, v in response.json().items()]
    heroes_names_list.sort()
    return heroes_names_list


def locate_turbo_quests():
    item_images = ["item_soul_ring.png", "item_midas.png"]
    for item in item_images:
        if pag.locateOnScreen(f"./images/{item}", confidence=0.9, region=(950, 500, 100, 360)):
            return True


def refresh_dota_plus_quests():
    log.info("--- Starting the Dota+ Refresh Script ---")
    time.sleep(3)
    hero_list = opendota_constants_heroes()
    for name in hero_list:
        left_mouse_click(XY_progress, 1.5)
        left_mouse_click(XY_refresh, 1.5, repeat=3)

        if locate_turbo_quests():
            log.info(name)

        time.sleep(2.0)
        pag.press("right")
    log.info("--- finished ---")


if __name__ == "__main__":
    refresh_dota_plus_quests()
