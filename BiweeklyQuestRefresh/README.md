# 👻 BiweeklyQuestRefresh

The script basically presses "Refresh challenges" button
and cycles over all Dota heroes, so you don't have to press this for all 120+ Dota 2 heroes yourself.

## 👆 How to use

- Navigate to any hero loadout page.
- Run the script with `.bat`-shortcut file in repo or just with `.py` file

## 🛞 Turbo Quests Addition

With extra `-t` flag the script can also try to recognize if a hero got one of special quests. Those quests are something like "Buy Soul Ring before 10:00/7:00/4:00" because you can actually complete those quests for 3 stars. You don't even need to commit to the item. Just buy and sell. It's easy to do in turbo because of inflated gold.

In this case:

- The script will also switch to Abaddon hero page and end on it.
- After exiting a small GUI-window will pop up with a list of heroes who have the quest.
- The script takes quite longer since now we need to think about OCRing the pictures.

## ✏️ TODO

- [ ] Midas picture is outdated.
