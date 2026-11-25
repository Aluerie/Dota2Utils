# 🖼️ HeroGrids

Unfortunately, Dota 2 UI does not allow for pixel-perfect alignment and
overall it is a bit annoying for slight OCD people like me.
This script solves the problem.

Of course, the hero grids included in code are *my personal* choice and *my personal* arrangement but the code is there:
edit the `*_layout` functions and the grid/category names in [main.py](./src/hero_grids/main.py) for yours.

It also keeps the str/agi/int/universal categories (unnamed categories on the right of the roles grid) correct:
heroes whose primary attribute changed in a patch are moved, new heroes are added, and each category is sorted alphabetically.

## 🚀 Usage

```sh
uv run HeroGrids
```

Before changing anything, it saves a timestamped backup of your current grid to `HeroGrids/.temp/backups/`
(the 20 newest backups are kept). If the grids are already as they should be, it does nothing.
