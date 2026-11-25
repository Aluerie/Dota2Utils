from __future__ import annotations

import asyncio
import datetime as dt
import json
import pathlib
from dataclasses import dataclass

import click
from steam.ext.dota2 import Hero

from dota2utils_common import ConfigError, Dota2UtilsError, config, datafeed, guides, steam
from dota2utils_common.logs import logger, setup_logging

from . import api_clients, item_build
from .const import Role
from .stratz import StratzClient

# ItemBuilds/src/item_builds/main.py -> ItemBuilds/state.json
STATE_FILE = pathlib.Path(__file__).resolve().parents[2] / "state.json"
# Pause between heroes; D2PT rate-limits aggressively;
SLEEP_BETWEEN_HEROES = 10.0


def load_hero_roles() -> dict[Hero, Role]:
    """Hero -> role pairs from `[item_builds.heroes]` in config.toml."""
    raw: dict[str, str] = config.section("item_builds").get("heroes") or {}
    if not raw:
        msg = "Add the heroes to update under `[item_builds.heroes]` in config.toml (see config.example.toml)."
        raise ConfigError(msg)

    hero_roles: dict[Hero, Role] = {}
    for hero_name, role_name in raw.items():
        try:
            hero = Hero[hero_name]
        except KeyError:
            msg = f"Unknown hero `{hero_name}` in `[item_builds.heroes]`. Use steam.py names, i.e. `DrowRanger`."
            raise ConfigError(msg) from None
        try:
            hero_roles[hero] = Role[role_name]
        except KeyError:
            roles = ", ".join(f'"{r.name}"' for r in Role)
            msg = f"Unknown role `{role_name}` for {hero_name} in `[item_builds.heroes]`. Use one of: {roles}."
            raise ConfigError(msg) from None
    return hero_roles


def load_state() -> dict[str, str]:
    """Hero ID -> ISO time the hero's guide was last updated."""
    if not STATE_FILE.is_file():
        return {}
    with STATE_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict[str, str]) -> None:
    with STATE_FILE.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(state, f, ensure_ascii=False, indent=4)


async def early_match_items(
    hero: Hero,
    role: Role,
    d2pt: api_clients.D2PTClient,
    stratz: StratzClient | None,
) -> list[int]:
    """Which wand/bottle/bracer-like items to put into "Early": from D2PT matches, else Stratz, else none."""
    try:
        hero_matches = await d2pt.hero_matches(hero, role)
    except api_clients.REQUEST_ERRORS as exc:
        logger.warning("🔒 D2PT refused its match data ({}: {})", type(exc).__name__, exc)
    else:
        if hero_matches:
            return item_build.common_match_items(hero_matches)
        logger.warning("🫥 D2PT returned no matches for {} ({})", hero.display_name, role.name)

    if stratz is None:
        logger.warning("🫥 No Stratz token in config.toml to fall back to - skipping wand/bottle/bracer-like items.")
        return []
    try:
        shares = await stratz.item_purchase_shares(hero.id, role)
    except api_clients.REQUEST_ERRORS as exc:
        logger.warning("🫥 Stratz failed too ({}: {}) - skipping wand/bottle/bracer-like items.", type(exc).__name__, exc)
        return []
    if not shares:
        logger.warning(
            "🫥 Stratz has no item data for {} ({}) - skipping wand/bottle/bracer-like items.", hero.display_name, role.name
        )
    return item_build.common_shared_items(shares)


@dataclass(frozen=True, slots=True)
class Run:
    """What every hero in a run shares: API clients, the current patch and item names."""

    d2pt: api_clients.D2PTClient
    stratz: StratzClient | None
    gameplay_version: str
    item_names: dict[int, str]
    # Only show what would change, don't write guides;
    dry_run: bool = False


async def process_hero(hero: Hero, role: Role, run: Run) -> None:
    """Update the hero's guide with D2PT meta items for the role (creating the guide if needed)."""
    logger.info("🦸 Updating {} ({})", hero.display_name, role.name)
    item_overview = await run.d2pt.item_overview(hero, role)
    match_items = await early_match_items(hero, role, run.d2pt, run.stratz)

    guides_dir = steam.guides_dir()
    path = guides.find_guide(guides_dir, hero.slug_name)
    if path is None:
        path = guides.new_guide_path(guides_dir, hero.slug_name)
        build = guides.new_guide(hero.slug_name, friend_id=steam.friend_id(), gameplay_version=run.gameplay_version)
        if not run.dry_run:
            logger.info("📝 No guide for {} yet - creating {} (restart Dota 2 to see it)", hero.display_name, path.name)
    else:
        build = guides.load_guide(path)

    categories = item_build.categorize_items(
        item_overview,
        match_items,
        role,
        run.item_names,
        item_build.saved_additions(build),
    )
    if run.dry_run:
        changes = item_build.describe_changes(item_build.current_categories(build), categories)
        logger.info("🧪 {}: {}", hero.display_name, "would change:" if changes else "no item changes")
        for line in changes:
            logger.info("🧪     {}", line)
        return

    item_build.write_categories(build, categories, run.gameplay_version)
    guides.save_guide(build, path)


async def main(*, dry_run: bool = False) -> None:
    hero_roles = load_hero_roles()
    guides_dir = steam.guides_dir()
    if not guides_dir.is_dir():
        msg = f"Dota 2 guides folder not found: {guides_dir}. Create any hero guide in the Dota 2 client once."
        raise Dota2UtilsError(msg)

    # D2PT rate-limits aggressively, so a run can die midway;
    # we remember when each hero was updated and do the least recently updated ones first.
    state = load_state()
    never = dt.datetime.min.replace(tzinfo=dt.UTC)

    def last_updated(hero_role: tuple[Hero, Role]) -> dt.datetime:
        updated = state.get(str(hero_role[0].id))
        return dt.datetime.fromisoformat(updated) if updated else never

    d2pt = api_clients.D2PTClient()
    patches = await d2pt.patches()
    run = Run(
        d2pt=d2pt,
        stratz=StratzClient(token) if (token := config.section("stratz").get("token")) else None,
        gameplay_version=patches[0]["version"],
        item_names=datafeed.get_item_names(),
        dry_run=dry_run,
    )

    for hero, role in sorted(hero_roles.items(), key=last_updated):
        await process_hero(hero, role, run)
        if not dry_run:  # a dry run doesn't change the order of the next real run;
            state[str(hero.id)] = dt.datetime.now(dt.UTC).isoformat()
            save_state(state)
        await asyncio.sleep(SLEEP_BETWEEN_HEROES)

    if dry_run:
        logger.success("🧪 Dry run done - checked {} guides, nothing was written.", len(hero_roles))
    else:
        logger.success("🎉 Done - updated {} guides.", len(hero_roles))


@click.group(invoke_without_command=True)
@click.option("--dry-run", is_flag=True, help="Only show which items would change in each guide; write nothing.")
@click.pass_context
def cli(ctx: click.Context, *, dry_run: bool) -> None:
    """Update Dota 2 hero guides with meta item builds from Dota 2 ProTracker."""
    setup_logging()
    if ctx.invoked_subcommand is None:
        try:
            asyncio.run(main(dry_run=dry_run))
        except Dota2UtilsError as exc:
            logger.error(str(exc))
            raise SystemExit(1) from exc


async def draft_worker() -> None:
    pass


@cli.command()
def draft() -> None:
    """Sandbox playground for experiments: `uv run ItemBuilds draft`."""
    asyncio.run(draft_worker())
