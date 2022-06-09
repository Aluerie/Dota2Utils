""" Dota Plus Quests Refresh

Just navigate to any hero page and open "Progress" tab there so 
the script can press "Refresh challenges" button and 
press "Right" key to switch to the next hero ;

time.sleep() values can be tweaked

You can run the script in python or with `.bat`-shortcut file in repo 
"""

import pyautogui as pag
import time
import requests

# 1920x1080 resolution
X, Y = 1145, 763

def opendota_constants_heroes():
    endpoint = 'https://api.opendota.com/api/constants/heroes'
    response = requests.get(endpoint)
    return response.json()

def refresh_dota_plus_quests(amount_of_heroes):
    time.sleep(3)
    for _ in range(amount_of_heroes):
        time.sleep(0.5)
        for _ in range(3):
            pag.click(x=X, y=Y)
            time.sleep(0.1)
        time.sleep(0.5)
        pag.press('right')


if __name__ == '__main__': 
    dota_dict = opendota_constants_heroes()
    amount_of_heroes = len(dota_dict)
    refresh_dota_plus_quests(amount_of_heroes)