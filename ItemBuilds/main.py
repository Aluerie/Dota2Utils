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
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        url = f"https://dota2protracker.com/hero/{hero.loc_name}"
        page.goto(url, wait_until="networkidle")

        # A bit hacky but it seems D2PT doubles labels for buttons so `f'{role} {role}'` works;
        # Select proper Role, it will open "Builds" tab by default
        page.get_by_role("button", name=f"{role} {role}").click()
        time.sleep(5.0)
        builds_html = page.content()

        # Item Stats tab
        page.get_by_role("button", name="Item Stats").click()
        time.sleep(5.0)
        item_stats_html = page.content()
        browser.close()
    return builds_html, item_stats_html


def save_soup(soup: BeautifulSoup) -> None:
    with pathlib.Path("./.to_delete/out.html").open("w", encoding="utf-8") as f:
        print(soup.prettify(), file=f)


def web_scrape_meta_items(builds_html: str, item_stats_html: str) -> MetaItems:
    """
    Docstring for web_scrape_meta_items

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
        msg = "Somehow found zero meta items."
        raise errors.MyError(msg)

    # 2. Builds
    soup = BeautifulSoup(builds_html, "html.parser")
    soup_items = soup.find_all("div", attrs={"class": "flex p-2 items-center justify-start svelte-zh3yuz"})
    for item in soup_items:
        if tag := item.find("img"):
            # 1. Item Name
            item_name = str(tag["src"]).removesuffix(".png").rsplit("/", 1)[-1]

            # For some reason, D2PT does NOT include these items into Item Stats tab;
            # But I mean, they are still important;
            if item_name in {
                "aghanims_shard",
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


def open_build_file(hero: api.Hero) -> tuple[vdf.VDFDict, pathlib.Path]:
    # Find the `.build` file for our specific hero
    for file in pathlib.Path(rf"C:\Program Files (x86)\Steam\userdata\{FRIEND_ID}\570\remote\guides").iterdir():
        if file.name.startswith(hero.slug_name):
            guide_path = file
            break
    else:
        msg = f"Please, create a hero guide for hero {hero.loc_name} manually first."
        raise errors.MyError(msg)

    # Open `.build` file
    with guide_path.open(encoding="utf-8") as f:
        return vdf.parse(f, mapper=vdf.VDFDict), guide_path


def get_patch_number() -> str:
    endpoint = "https://www.dota2.com/datafeed/patchnoteslist"
    response = requests.get(endpoint, timeout=20)
    data = response.json()
    return data["patches"][-1]["patch_number"]


def edit_the_build(build: vdf.VDFDict, meta_items: MetaItems, role: enums.RoleEnum) -> vdf.VDFDict:
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
    with guide_path.open("w", encoding="utf-8") as f:
        vdf.dump(build, f, pretty=True)


def create_build(hero: api.Hero, role: enums.RoleEnum) -> None:
    builds_html, item_stats_html = get_html(hero, role)
    try:
        meta_items = web_scrape_meta_items(builds_html, item_stats_html)
    except errors.MyError:
        log.exception("Failed to make a build for hero %s: Meta items were not found", hero)
        raise

    build, guide_path = open_build_file(hero)
    build = edit_the_build(build, meta_items, role)
    export(build, guide_path)


@click.group()
def cli() -> None:
    pass


@cli.command()
def main() -> None:
    all_heroes = api.get_or_fetch_heroes()

    for hero, role in CONFIG_HEROES:
        try:
            create_build(all_heroes[hero], role)
        except errors.MyError:
            continue

    log.info("✅ Done creating builds.")


@cli.command(name="draft")
def draft() -> None:
    pass


if __name__ == "__main__":
    cli()
