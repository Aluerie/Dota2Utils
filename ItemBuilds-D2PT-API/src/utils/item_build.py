from __future__ import annotations

import datetime
import logging
import operator
import pathlib
from typing import TYPE_CHECKING

import vdf

from config import FRIEND_ID

from . import const, errors

if TYPE_CHECKING:
    from steam.ext.dota2 import Hero
    from typings import api_schemas

log = logging.getLogger()
log.setLevel(logging.INFO)


def open_item_build(hero: Hero) -> tuple[vdf.VDFDict, pathlib.Path]:
    """Open local `.build` file for the hero."""
    for file in pathlib.Path(rf"C:\Program Files (x86)\Steam\userdata\{FRIEND_ID}\570\remote\guides").iterdir():
        if file.name.startswith(hero.slug_name):
            guide_path = file
            break
    else:
        # I'm being extremely lazy with this one;
        msg = f"Please, create a hero guide for hero {hero.display_name} manually first."
        raise errors.MyError(msg)

    with guide_path.open(encoding="utf-8") as f:
        return vdf.parse(f, mapper=vdf.VDFDict), guide_path


def edit_item_build(
    build: vdf.VDFDict,
    item_overview: api_schemas.ItemOverview,
    role: const.Role,
    patches: api_schemas.Patches,
    item_id_name_mapping: dict[int, str],
    hero_matches: api_schemas.Matches,
) -> vdf.VDFDict:
    """Edit item build using meta items data."""
    log.debug("Editing the item build")

    # Title
    current_patch = patches[0]["version"]
    build["guidedata"][0, "Title"] = (
        f"Updated: {datetime.datetime.now(tz=datetime.UTC).strftime('%d %b %y')}; {current_patch}"
    )
    try:
        my_saved: list[str] = build["guidedata"]["ItemBuild"]["Items"]["My additions"].get_all_for("item")
    except KeyError:
        my_saved = []

    def render_vdf_dict(items: list[str] | tuple[str, ...]) -> vdf.VDFDict:
        return vdf.VDFDict([("item", item) for item in items])

    # Item Build with items from `item_overview`
    build["guidedata"]["ItemBuild"][0, "Items"] = vdf.VDFDict([])

    meta_name = f"Meta: {role.name}"
    categories: dict[str, list[str]] = {
        "Consumables": const.CONSUMABLES,
        "Early": ["item_boots"],  # Boots are always there;
        meta_name: [],
        "Low Percent (<5%)": [],
        "My additions": my_saved,
    }

    def append_item(category: str, item: api_schemas.Item) -> None:
        categories[category].append(f"item_{item_id_name_mapping[item['item_id']]}")

    for item in item_overview["overviewRows"]:
        if item["hero_purchase_rate"] > 0.103 and item["best_order"]["avg_minute"] < 15.6:
            append_item("Early", item)
        elif 0.013 <= item["hero_purchase_rate"] < 0.05:
            append_item("Low Percent (<5%)", item)
        elif item["hero_purchase_rate"] < 0.013:
            # Items below 1.3% are ignored; People start buying all kinds of crap here.
            continue
        else:
            append_item(meta_name, item)

    # Some edits with items from `hero_matches`
    exception_items = {
        # "aghanims_shard",
        41: 0,  # "bottle",
        36: 0,  # "magic_wand",
        73: 0,  # "bracer",
        75: 0,  # "wraith_band",
        77: 0,  # "null_talisman",
        244: 0,  # "wind_lace",
    }
    for match in hero_matches:
        for item in match["data"]["items"]:
            if item["item_id"] in exception_items:
                exception_items[item["item_id"]] += 1

    for item_id, purchases in sorted(exception_items.items(), key=operator.itemgetter(1), reverse=True):
        if purchases / len(hero_matches) < 0.2:
            break
        categories["Early"].append(f"item_{item_id_name_mapping[item_id]}")

    for category, items in categories.items():
        build["guidedata"]["ItemBuild"]["Items"][category] = render_vdf_dict(items)

    return build


def export_item_build(build: vdf.VDFDict, guide_path: pathlib.Path) -> None:
    """Save the build to the local file in steam folder."""
    with guide_path.open("w", encoding="utf-8") as f:
        vdf.dump(build, f, pretty=True)
