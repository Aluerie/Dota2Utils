from __future__ import annotations

import datetime
import logging
import pathlib
import time
from operator import itemgetter
from typing import TYPE_CHECKING

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

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


CONSUMABLES: tuple[str, ...] = (
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
)


def get_html(hero: api.Hero, role: enums.RoleEnum) -> tuple[str, str]:
    """Get HTML content to be web-scraped later.

    This loads meta page for the hero on Dota2ProTracker for the demanded role
    and gets content for "Builds" and "Item Stats" sub-tabs.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        url = f"https://dota2protracker.com/hero/{hero.loc_name}"
        page.goto(url, wait_until="networkidle")

        # Select proper Role tab, it will open "Builds" sub-tab by default;
        # A bit hacky but it seems D2PT doubles labels for buttons so `f'{role} {role}'` works;
        page.get_by_role("button", name=f"{role} {role}").click()
        time.sleep(5.0)  # This is needed, the data is slow to load.
        builds_html = page.content()

        # Item Stats tab
        page.get_by_role("button", name="Item Stats").click()
        time.sleep(5.0)  # This is needed, the data is slow to load.
        item_stats_html = page.content()
        browser.close()
    return builds_html, item_stats_html


def save_soup(soup: BeautifulSoup) -> None:
    """Save soup to a local file for easier inspection in a text editor."""
    with pathlib.Path("./.to_delete/out.html").open("w", encoding="utf-8") as f:
        print(soup.prettify(), file=f)


def web_scrape_meta_items(builds_html: str, item_stats_html: str) -> MetaItems:
    """Web-scrape meta items from supplied HTML content.

    Meta Items should include item names, their purchase rate and average time of purchase.
    This data is used to group and sort items into the Dota 2 item builds.

    Warning
    -------
    EXTREMELY VOLATILE CODE. IF D2PT CHANGES ANYTHING - IT'S COOKED.
    """

    # 1. Item Stats
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
            m, s = str(siblings[3].contents[0]).strip().split(":")
            avg_time = 60 * int(m) + int(s)
            log.debug("%s", (f"item_{item_name}", purchase_rate, avg_time))
            meta_items.append((f"item_{item_name}", purchase_rate, avg_time))
        else:
            log.warning("tag is empty for item %s", item)

    if not meta_items:
        msg = "Somehow Web Scraping failed to find meta items on the page."
        raise errors.MyError(msg)

    # 2. Builds
    soup = BeautifulSoup(builds_html, "html.parser")
    soup_items = soup.find_all("div", attrs={"class": "flex p-2 items-center justify-start svelte-zh3yuz"})
    for item in soup_items:
        if tag := item.find("img"):
            # 1. Item Name
            item_name = str(tag["src"]).removesuffix(".png").rsplit("/", 1)[-1]

            # For some reason(-s), D2PT does NOT include these items into Item Stats tab;
            # But I mean, they are still important;
            if item_name in {
                "aghanims_shard",  # I'm not really sure how to handle Aghanims Shard situation `purchase_rate` wise
                "bottle",
                "magic_wand",
                "bracer",
                "null_talisman",
                "wraith_band",
            }:
                siblings = item.find_next_siblings()
                # 2. Purchase Rate
                purchase_rate = (
                    55.0 if "CORE" in (pr := str(siblings[0].contents[0])) else float(pr.strip().removesuffix("%"))
                )
                # 3. Avg Time
                if average_time_div := siblings[1].find("div"):
                    average_time = int(str(average_time_div.contents[0]).strip().removesuffix("m")) * 60
                else:
                    msg = "Empty"
                    raise errors.MyError(msg)

                log.debug("%s", (f"item_{item_name}", purchase_rate, average_time))
                meta_items.append((f"item_{item_name}", purchase_rate, average_time))
        else:
            log.warning("tag is empty for item %s", item)

    return sorted(meta_items, key=itemgetter(1), reverse=True)


def open_item_build(hero: api.Hero) -> tuple[vdf.VDFDict, pathlib.Path]:
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
    endpoint = "https://www.dota2.com/datafeed/patchnoteslist"
    response = requests.get(endpoint, timeout=20)
    data = response.json()
    return data["patches"][-1]["patch_number"]


def edit_item_build(build: vdf.VDFDict, meta_items: MetaItems, role: enums.RoleEnum) -> vdf.VDFDict:
    """Edit item build using meta items data."""

    # Title
    build["guidedata"][0, "Title"] = (
        f"Updated: {datetime.datetime.now(tz=datetime.UTC).strftime('%d %b %y')}; {get_patch_number()}"
    )

    def render_vdf_dict(items: list[str] | tuple[str, ...]) -> vdf.VDFDict:
        return vdf.VDFDict([("item", item) for item in items])

    # Item Build
    build["guidedata"]["ItemBuild"][0, "Items"] = vdf.VDFDict([])
    build["guidedata"]["ItemBuild"]["Items"]["Consumables"] = render_vdf_dict(CONSUMABLES)

    # Sort Meta Items
    early: list[str] = []
    meta: list[str] = []
    low_percent: list[str] = []
    for item_name, purchase_rate, avg_time in meta_items:
        if avg_time < 15 * 60 + 30 and purchase_rate > 5:
            # Items bought before 15:30 will be considered as "Early"
            early.append(item_name)
        elif 1.3 < purchase_rate < 3:
            # Items belonging to (1.3%, 3%) group are "Low Percent";
            low_percent.append(item_name)
        elif purchase_rate < 1.3:
            # Items below 1.3% are ignored;
            continue
        else:
            # The rest are meta;
            meta.append(item_name)

    build["guidedata"]["ItemBuild"]["Items"]["Early"] = render_vdf_dict(early)
    build["guidedata"]["ItemBuild"]["Items"][f"Meta: {role}"] = render_vdf_dict(meta)
    build["guidedata"]["ItemBuild"]["Items"]["Low Percent"] = render_vdf_dict(low_percent)
    return build


def export(build: vdf.VDFDict, guide_path: pathlib.Path) -> None:
    """Save the build to the local file in steam folder."""
    with guide_path.open("w", encoding="utf-8") as f:
        vdf.dump(build, f, pretty=True)


def create_item_build(hero: api.Hero, role: enums.RoleEnum) -> None:
    """Create the item build for the hero + role pairing.

    This function calls other functions in a proper sequence.
    """
    builds_html, item_stats_html = get_html(hero, role)
    try:
        meta_items = web_scrape_meta_items(builds_html, item_stats_html)
    except errors.MyError:
        log.warning("⚠️ Failed to make a build for hero %s: Meta items were not found", hero)
        raise

    build, guide_path = open_item_build(hero)
    build = edit_item_build(build, meta_items, role)
    export(build, guide_path)


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Main CLI command.

    Usage
    -----
    * uv run main.py
    """
    if ctx.invoked_subcommand is None:
        all_heroes = api.get_or_fetch_heroes()

        for hero, role in (progress_bar := tqdm(CONFIG_HEROES.items(), unit="hero", colour="#9678B6")):
            progress_bar.set_postfix_str(f'Current hero: {hero.name}')
            try:
                create_item_build(all_heroes[hero], role)
            except errors.MyError:
                # if failed to make a build - skip the hero;
                continue

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
