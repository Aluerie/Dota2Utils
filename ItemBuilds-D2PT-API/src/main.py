from __future__ import annotations

import asyncio
import datetime
import json
import logging
import pathlib
from typing import TYPE_CHECKING

import click

from config import CONFIG_HEROES
from utils import api_clients, item_build

if TYPE_CHECKING:
    from steam.ext.dota2 import Hero
    from typings import api_schemas

    from utils.const import Role


logging.basicConfig(level=logging.DEBUG)

log = logging.getLogger()
log.setLevel(logging.INFO)


async def process_hero(
    hero: Hero,
    role: Role,
    item_id_name_mapping: dict[int, str],
    d2pt_client: api_clients.D2PTClient,
    patches: api_schemas.Patches,
) -> None:

    item_overview = await d2pt_client.item_overview(hero, role)

    hero_matches = await d2pt_client.hero_matches(hero, role)

    build, guide_path = item_build.open_item_build(hero)
    build = item_build.edit_item_build(
        build,
        item_overview,
        role,
        patches,
        item_id_name_mapping,
        hero_matches,
    )
    item_build.export_item_build(build, guide_path)


async def main() -> None:

    # We need state file because d2pt api is very aggressive with api rate limits
    # hence we need some kind of database of which heroes got processes when
    with pathlib.Path("src/state.json").open(encoding="utf-8") as f:
        state = json.load(f)

    def key(hr: tuple[Hero, Role]) -> datetime.datetime:
        if xd := state.get(str(hr[0].id), None):
            return datetime.datetime.fromisoformat(xd)
        return datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=500)

    heroes_to_process = sorted(
        CONFIG_HEROES.items(),
        key=key,
    )

    opendota_items = await api_clients.OpenDotaClient().get_items()
    item_id_name_mapping = {item["id"]: name for name, item in opendota_items.items()}

    d2pt_client = api_clients.D2PTClient()
    patches = await d2pt_client.patches()

    for hero, role in heroes_to_process:
        await process_hero(hero, role, item_id_name_mapping, d2pt_client, patches)

        state[str(hero.id)] = datetime.datetime.now(datetime.UTC)
        with pathlib.Path("src/state.json").open("w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=4, default=str)

        await asyncio.sleep(10.0)


@click.group(invoke_without_command=True)
@click.pass_context
def cli(_: click.Context) -> None:
    asyncio.run(main())


async def draft_worker() -> None:
    pass


@cli.command()
def draft() -> None:
    """Draft CLI command.

    I lazily use it for some sandbox playground purposes.

    Usage
    -----
    * uv run main.py draft
    """
    asyncio.run(draft_worker())


if __name__ == "__main__":
    cli()
