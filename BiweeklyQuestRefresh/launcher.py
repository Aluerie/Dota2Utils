import click

import time
from utils import const, helpers

import pyautogui
import easygui


@click.command()
@click.option("--turbo", "-t", is_flag=True, help="Also do turbo quests recognition", flag_value=True, default=False)
@click.option("--resolution", "-r", default="1920_1080", help="Resolution", type=click.STRING)
def refresh_dota_plus_quests(turbo: bool, resolution: str):
    print("--- Starting the Dota+ Refresh Script ---")
    try:
        resolution_data = const.RESOLUTION_MAPPING[resolution]
    except KeyError:
        supported_resolutions = ", ".join(const.RESOLUTION_MAPPING.keys())
        print(f"Provided resolution is not supported. \nSupported resolutions: {supported_resolutions}")
        return

    time.sleep(2.0)
    hero_list = helpers.get_opendota_constants_heroes()

    title = "Biweekly D+ Quest Refresh"

    if turbo:
        # if turbo flag is on then we also look for special quests
        pyautogui.typewrite("Abaddon")
        time.sleep(0.5)

        turbo_quest_hero_names = []
        helpers.mouse_left_click(resolution_data.progress_tab, repeat=3)
        for name in hero_list:
            helpers.mouse_left_click(resolution_data.refresh_button, 1.5, repeat=3)
            if helpers.is_turbo_quest_located(region=resolution_data.challenges_region):
                turbo_quest_hero_names.append(name)
            pyautogui.press("right")
            time.sleep(1.0)

        display = "Heroes with special Turbo Quests\n" + "\n".join(turbo_quest_hero_names)
        easygui.msgbox(display, title=title, ok_button="OK!")
    else:
        # if turbo flag is off then we can just click around quickly
        helpers.mouse_left_click(resolution_data.progress_tab, repeat=3)
        for name in hero_list:
            helpers.mouse_left_click(resolution_data.refresh_button, 0.1, repeat=3)
            # pyautogui.press("right")
            helpers.mouse_left_click(resolution_data.next_hero, 0.1) # ceown fall
            time.sleep(0.3)

        # easygui.msgbox('Done!', title=title, ok_button="OK!")

    print("--- Finished ---")


if __name__ == "__main__":
    refresh_dota_plus_quests()
