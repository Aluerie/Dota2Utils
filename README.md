# 🔧 Dota2Utils

🔧 Each folder in this repository is a small utility for Dota 2.

## 🧰 List of utilities

### [1.➕ DotaPlusQuests](./DotaPlusQuests)

Script that auto-clicks "Refresh challenges" for Dota Plus hero quests.

### [2.🖼️ HeroGrids](./HeroGrids)

Edit custom Hero Grids and align categories as you wish. The hero grids it builds are personal (my preferences, my heroes), but hey, the code is there.

> [!TIP]
> If you want some meta hero grids - use something like [dota2protracker.com/meta-hero-grids](<https://dota2protracker.com/meta-hero-grids>), [github.com/maybewewill/metagrid](<https://github.com/maybewewill/metagrid>), etc.

### [3.🔨 ItemBuilds](./ItemBuilds)

Import meta item builds from Dota 2 ProTracker right into your Dota 2 Client hero builds.

> [!NOTE]
> Uses D2PT's somewhat public API hence it should be fine with their ToS.

### [4.😳 ListEmoticons](./ListEmoticons)

Updated fork of
[ListEmoticons.ipynb](https://github.com/rossengeorgiev/dota2_notebooks/blob/master/List%20Emoticons.ipynb)
notebook by [@rossengeorgiev](https://github.com/rossengeorgiev).
You can see all the emotes at
[aluerie.github.io/Dota2Utils/ListEmoticons/](https://aluerie.github.io/Dota2Utils/ListEmoticons/)

### [5.🧦 SocialFeed](./SocialFeed)

Send messages into your User Feed Profile Widget.
Valve removed UI to do it directly in the client, but it's still possible with a script like this.

## 📦 Setup

The tools are for Windows and need [uv](https://docs.astral.sh/uv/). uv installs the right Python (3.15) by itself.

1. Clone the repository and install everything:

   ```sh
   uv sync --all-packages
   ```

2. If a tool needs settings (ItemBuilds, ListEmoticons, SocialFeed), copy [config.example.toml](./config.example.toml) to `config.toml` and edit it.
   `config.toml` is git-ignored.

Your Steam folder, Steam account and Dota 2 install are detected automatically.
If detection picks the wrong ones, set them under `[steam]` in `config.toml`.

## 🚀 Usage

After the one-time `uv sync --all-packages` from the setup above, every tool runs by its name (from anywhere in the repository), see its README for details:

```sh
uv run ItemBuilds
```

| Tool | Command |
| --- | --- |
| DotaPlusQuests | `uv run DotaPlusQuests` |
| HeroGrids | `uv run HeroGrids` |
| ItemBuilds | `uv run ItemBuilds` |
| ListEmoticons | `uv run ListEmoticons` |
| SocialFeed | `uv run SocialFeed` |

## 🛠️ Development

The repository is a [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/): each tool folder is a package,
and [dota2utils-common](./dota2utils-common) holds the code they share (config, Steam paths, Valve's hero/item lists, hero guide files).
[docs/](./docs) is the GitHub Pages site (served from `main` + `/docs`); ListEmoticons writes its page and gifs there.

Checks (the same ones CI runs):

```sh
uv run ruff check
```

```sh
uv run ruff format --check
```

```sh
uv run ty check
```

```sh
uv run pytest
```
