# 🔨 ItemBuilds

Import meta item builds from [Dota 2 ProTracker](https://dota2protracker.com) into your Dota 2 client hero guides.

For every hero in your config, the guide gets these categories:

- **Consumables** - the usual consumables.
- **Early** - boots, plus items most players buy before ~15 minutes (including wand/bottle/bracer-like items, counted from recent high-MMR matches on D2PT, or from [Stratz](https://stratz.com) when D2PT refuses that data).
- **Meta: \<Role\>** - the core items for the role.
- **Low Percent (<5%)** - situational items.
- **My additions** - your own items; kept as they are between runs.

## 📦 Setup

1. Follow the setup in the [main README](../README.md#-setup).
2. List your heroes and roles under `[item_builds.heroes]` in `config.toml`.
3. Optional but recommended: put a free Stratz API token from [stratz.com/api](https://stratz.com/api) under `[stratz]` in `config.toml`.
   D2PT often refuses its match data; without a token those heroes just get no wand/bottle/bracer-like items in "Early".

Heroes without a guide get one created automatically (restart Dota 2 to see new guides).

## 🚀 Usage

```sh
uv run ItemBuilds
```

Heroes are processed least-recently-updated first, and progress is saved to `ItemBuilds/state.json` after each hero,
so a run interrupted by D2PT rate limits picks up where it left off next time.

To only see what would change, without writing any guide:

```sh
uv run ItemBuilds --dry-run
```

It prints the items each category would gain (`+`) and lose (`-`), e.g. `Early: +magic_wand -bracer`.
