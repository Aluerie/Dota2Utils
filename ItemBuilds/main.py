from __future__ import annotations

import datetime
import logging
import pathlib
import time
from contextlib import contextmanager
from logging.handlers import RotatingFileHandler
from operator import itemgetter
from typing import TYPE_CHECKING, Any

import click
import requests
import vdf
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from tqdm import tqdm

from config import CONFIG_HEROES, FRIEND_ID
from utils import api, enums, errors

if TYPE_CHECKING:
    type MetaItems = list[tuple[str, float, int]]
    from collections.abc import Generator

log = logging.getLogger()
log.setLevel(logging.INFO)


@contextmanager
def setup_logging() -> Generator[Any, Any, Any]:
    """Setup logging."""

    try:
        fmt = logging.Formatter(
            "%(asctime)s %(levelname)-4.4s %(name)-30s %(lineno)-4d %(funcName)-35s %(message)s",
            "%H:%M:%S %d/%m",
        )

        # Stream Handler
        handler = logging.StreamHandler()
        handler.setFormatter(fmt)
        log.addHandler(handler)

        # ensure logs folder
        pathlib.Path(".temp/").mkdir(parents=True, exist_ok=True)
        # File Handler
        file_handler = RotatingFileHandler(
            filename=".temp/items.log",
            encoding="utf-8",
            mode="w",
            maxBytes=7 * 1024 * 1024,
            backupCount=1,
        )
        file_handler.setFormatter(fmt)
        log.addHandler(file_handler)

        yield
    finally:
        # __exit__
        handlers = log.handlers[:]
        for h in handlers:
            h.close()
            log.removeHandler(h)


CONSUMABLES: list[str] = [
    "item_tpscroll",
    "item_flask",
    "item_tango",
    "item_faerie_fire",
    "item_blood_grenade",
    "item_clarity",
    "item_enchanted_mango",
    "item_infused_raindrop",
    "item_ward_observer",
    "item_ward_sentry",
    "item_dust",
    "item_smoke_of_deceit",
]


def get_html(hero: api.OpendotaHero, role: enums.Role) -> tuple[str, str]:
    """Get HTML content to be web-scraped later.

    This loads meta page for the hero on Dota2ProTracker for the demanded role
    and gets content for "Builds" and "Item Stats" sub-tabs.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        url = f"https://dota2protracker.com/hero/{hero.loc_name}"
        page.goto(url, wait_until="networkidle")

        # So currently a hero page (for example, https://dota2protracker.com/hero/Luna)
        # looks like this
        # ---------------------------------------------------------------------
        #                                  LUNA
        #      All Roles | *Carry* | Mid | Offlane | Support | Hard Support     <-- 6 Role Buttons
        # ---------------------------------------------------------------------
        # * Some Stats *
        # ---------------------------------------------------------------------
        # Builds | Meta Analysis | Matchups & Synergies | Item Stats | Off-Meta <-- 5 Analysis-related Sub-tabs
        # ---------------------------------------------------------------------
        #
        # We are interested in clicking those things:
        #   1. A proper Role button;
        #   2. "Builds" (loads by default) and "Item Stats" sub-tabs;

        # 1. Select proper Role button, it will open "Builds" sub-tab by default;
        # A bit hacky but it seems D2PT doubles labels for buttons so `f"{role} {role}"` works;
        page.get_by_role("button", name=f"{role} {role}").click()
        time.sleep(5.1)  # Needed, the data is slow to load (Otherwise shows "Loading" string instead of the data).
        builds_html = page.content()

        # 2. Item Stats sub-tab
        page.get_by_role("button", name="Item Stats").click()
        time.sleep(5.1)  # Needed, the data is slow to load.
        item_stats_html = page.content()
        browser.close()
    return builds_html, item_stats_html


def save_soup(soup: BeautifulSoup) -> None:
    """Save soup to a local file (i.e. for an easier inspection in a text editor)."""
    with pathlib.Path("./.to_delete/out.html").open("w", encoding="utf-8") as f:
        print(soup.prettify(), file=f)


def web_scrape_meta_items(builds_html: str, item_stats_html: str) -> MetaItems:
    """Web-scrape meta items from supplied HTML content.

    Meta Items data should include item names, their purchase rate and average time of purchase.
    It is used to group and sort items in the Dota 2's in-game item build guides.

    Warning
    -------
    EXTREMELY VOLATILE CODE.
    IF D2PT CHANGES ANYTHING - IT'S COOKED.
    """

    # 1. "Item Stats" sub-tab
    soup = BeautifulSoup(item_stats_html, "html.parser")
    soup_items = soup.find_all("div", attrs={"class": "flex p-2 items-center justify-start items-center svelte-zh3yuz"})

    meta_items: MetaItems = []
    for item in soup_items:
        if tag := item.find("img"):
            # 1. Item Name
            item_name = str(tag["src"]).removesuffix(".png").rsplit("/", 1)[-1]
            siblings = item.find_next_siblings()
            # 2. Purchase Rate
            purchase_rate = float(str(siblings[1].contents[0]).strip().removesuffix("%"))
            # 3. Avg Time
            minutes, seconds = str(siblings[3].contents[0]).strip().split(":")
            avg_time = 60 * int(minutes) + int(seconds)
            log.debug("%s", (f"item_{item_name}", purchase_rate, avg_time))
            meta_items.append((f"item_{item_name}", purchase_rate, avg_time))
        else:
            log.warning("tag is empty for item %s", item)

    if not meta_items:
        msg = "Somehow Web Scraping failed to find meta items on the page."
        raise errors.MyError(msg)

    # 2. "Builds" sub-tab
    soup = BeautifulSoup(builds_html, "html.parser")
    soup_items = soup.find_all("div", attrs={"class": "flex p-2 items-center justify-start svelte-zh3yuz"})

    start_core_assumption: float = 60.0  # let's assume that the highest "core" item has 60% purchase rate;
    for item in soup_items:
        if tag := item.find("img"):
            # 1. Item Name
            item_name = str(tag["src"]).removesuffix(".png").rsplit("/", 1)[-1]

            # For some reason(-s), D2PT does NOT include these items into "Item Stats" sub-tab;
            if item_name in {
                # Not sure how to handle Aghanims Shard situation `purchase_rate` wise
                # It's unclear how to separate actual purchases versus tormentor drops stats-wise.
                # It's also useless to separate them because people may force tormentor
                # because it drops good shards as one of the reasons.
                # So usually high purchase rate for aghanims shard means that
                # the shard is either bought or dropped by tormentor often enough.
                "aghanims_shard",
                "bottle",
                "magic_wand",
                "bracer",
                "null_talisman",
                "wraith_band",
            }:
                siblings = item.find_next_siblings()
                # 2. Purchase Rate
                # D2PT hides purchase rate for items that are marked as "CORE".
                # Therefore let's make a bald assumption about their purchase rate.
                # It doesn't match well with "Item Stats" tab, but it still lands just fine in the item builds.
                purchase_rate = (
                    start_core_assumption
                    if "CORE" in (pr := str(siblings[0].contents[0]))
                    else float(pr.strip().removesuffix("%"))
                )
                start_core_assumption -= 1
                # 3. Avg Time
                if average_time_div := siblings[1].find("div"):
                    average_time = int(str(average_time_div.contents[0]).strip().removesuffix("m")) * 60
                else:
                    msg = "average_time appears to be empty"
                    raise errors.MyError(msg)

                log.debug("%s", (f"item_{item_name}", purchase_rate, average_time))
                meta_items.append((f"item_{item_name}", purchase_rate, average_time))
        else:
            log.warning("tag is empty for item %s", item)

    return sorted(meta_items, key=itemgetter(1), reverse=True)


def open_item_build(hero: api.OpendotaHero) -> tuple[vdf.VDFDict, pathlib.Path]:
    """Open local `.build` file for the hero."""
    for file in pathlib.Path(rf"C:\Program Files (x86)\Steam\userdata\{FRIEND_ID}\570\remote\guides").iterdir():
        if file.name.startswith(hero.slug_name):
            guide_path = file
            break
    else:
        # I'm being extremely lazy with this one;
        msg = f"Please, create a hero guide for hero {hero.loc_name} manually first."
        raise errors.MyError(msg)

    with guide_path.open(encoding="utf-8") as f:
        return vdf.parse(f, mapper=vdf.VDFDict), guide_path


def get_patch_number() -> str:
    """Get current patch number for future reference."""
    log.info("Getting Dota 2 current patch number")
    endpoint = "https://www.dota2.com/datafeed/patchnoteslist"
    for _ in range(5):
        # why it loves erroring on the very first request ?! Valve, please.
        try:
            response = requests.get(endpoint, timeout=10)
            break
        except requests.ReadTimeout:
            time.sleep(0.49)
            continue
    else:
        msg = "Could not reach dota2.com to get the current patch number."
        raise errors.MyError(msg)

    data = response.json()
    return data["patches"][-1]["patch_number"]


def edit_item_build(build: vdf.VDFDict, meta_items: MetaItems, role: enums.Role, current_patch: str) -> vdf.VDFDict:
    """Edit item build using meta items data."""
    log.debug("Editing the item build")

    # Title
    build["guidedata"][0, "Title"] = (
        f"Updated: {datetime.datetime.now(tz=datetime.UTC).strftime('%d %b %y')}; {current_patch}"
    )
    try:
        my_saved: list[str] = build["guidedata"]["ItemBuild"]["Items"]["My additions"].get_all_for("item")
    except KeyError:
        my_saved = []

    def render_vdf_dict(items: list[str] | tuple[str, ...]) -> vdf.VDFDict:
        return vdf.VDFDict([("item", item) for item in items])

    # Item Build
    build["guidedata"]["ItemBuild"][0, "Items"] = vdf.VDFDict([])

    meta_name = f"Meta: {role}"
    categories: dict[str, list[str]] = {
        "Consumables": CONSUMABLES,
        "Early": [],
        meta_name: [],
        "Low Percent (<5%)": [],
        "My additions": my_saved,
    }

    # Sort Meta Items and assign them into either
    # Early, meta_name or Low Percent category;
    for item_name, purchase_rate, avg_time in meta_items:
        # The numbers in the following conditions are subject to change
        if avg_time < 15 * 60 + 30 and purchase_rate > 10.3:
            # Items bought before 15:30 and commonly bought will be considered as "Early"
            categories["Early"].append(item_name)
        elif 1.3 < purchase_rate < 5:
            # Items belonging to (1.3%, 5%) group are "Low Percent";
            categories["Low Percent (<5%)"].append(item_name)
        elif purchase_rate < 1.3:
            # Items below 1.3% are ignored; People start buying all kinds of crap here.
            continue
        else:
            # The rest are meta;
            categories[meta_name].append(item_name)

    for category, items in categories.items():
        build["guidedata"]["ItemBuild"]["Items"][category] = render_vdf_dict(items)

    return build


def export(build: vdf.VDFDict, guide_path: pathlib.Path) -> None:
    """Save the build to the local file in steam folder."""
    with guide_path.open("w", encoding="utf-8") as f:
        vdf.dump(build, f, pretty=True)


def create_item_build(hero: api.OpendotaHero, role: enums.Role, current_patch: str) -> None:
    """Create the item build for the hero + role pairing.

    This function calls other functions in a proper sequence.
    """
    builds_html, item_stats_html = get_html(hero, role)
    meta_items = web_scrape_meta_items(builds_html, item_stats_html)
    build, guide_path = open_item_build(hero)
    build = edit_item_build(build, meta_items, role, current_patch)
    export(build, guide_path)


def loop_over_heroes(
    heroes_roles: dict[enums.Hero, enums.Role],
    colour: str,
    all_heroes: dict[int, api.OpendotaHero],
    current_patch: str,
) -> dict[enums.Hero, enums.Role]:
    """Loop over heroes and make Dota 2 item builds."""
    failed: dict[enums.Hero, enums.Role] = {}
    for hero, role in (
        progress_bar := tqdm(
            heroes_roles.items(),
            unit="hero",
            colour=colour,
            bar_format="{l_bar}{bar:30}{r_bar}{bar:-30b}",
        )
    ):
        progress_bar.set_postfix_str(f"Current hero: {hero.name}")
        try:
            create_item_build(all_heroes[hero], role, current_patch)
        except errors.MyError as error:
            # if failed to make a build - skip the hero;
            failed[hero] = role
            log.warning("⚠️ Failed to make a build for hero %r: %s", hero, error)
            continue
    return failed


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Main CLI command.

    Usage
    -----
    * uv run main.py
    """
    if ctx.invoked_subcommand is None:
        with setup_logging():
            all_heroes = api.get_or_fetch_heroes()
            current_patch = get_patch_number()

            # Loop once
            failed = loop_over_heroes(CONFIG_HEROES, "#9678B6", all_heroes, current_patch)

            # It's fine if it failed somewhere - try one more time
            if failed:
                log.info("🟨 Retrying creating a build for failed hero-role pairs: %s.", failed)
                failed = loop_over_heroes(failed, "#A6B64C", all_heroes, current_patch)

            if failed:
                log.info("🟥 Failed twice to make a build for hero-role pairs: %s.", failed)

            log.info("✅ Done creating builds.")


@cli.command()
def draft() -> None:
    """Draft CLI command.

    I lazily use it for some sandbox playground purposes.

    Usage
    -----
    * uv run main.py draft
    """

    log.info("✅ Done executing draft.")


if __name__ == "__main__":
    cli()
