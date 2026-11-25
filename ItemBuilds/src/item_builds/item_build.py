from __future__ import annotations

import datetime as dt
from collections import Counter
from typing import TYPE_CHECKING

import vdf

from dota2utils_common.logs import logger

from . import const

if TYPE_CHECKING:
    from . import api_schemas

# Items bought by more than this share of the hero's players...
EARLY_MIN_PURCHASE_RATE = 0.103
# ...before this minute (on average) go into the "Early" category;
EARLY_MAX_AVG_MINUTE = 15.6
# Items bought by fewer players than this go into the "Low Percent" category;
LOW_PERCENT_MAX_PURCHASE_RATE = 0.05
# Items bought by fewer players than this are ignored - people start buying all kinds of crap here;
IGNORE_MAX_PURCHASE_RATE = 0.013
# Early-game items D2PT doesn't list in the item overview, so we count them in recent D2PT matches instead
# (or in Stratz purchase stats when D2PT refuses the matches).
# They make it into "Early" if they show up in at least `MATCH_ITEMS_MIN_SHARE` of matches.
MATCH_ITEMS: dict[int, str] = {
    41: "bottle",
    36: "magic_wand",
    73: "bracer",
    75: "wraith_band",
    77: "null_talisman",
    244: "wind_lace",
}
MATCH_ITEMS_MIN_SHARE = 0.2

EARLY = "Early"
LOW_PERCENT = "Low Percent (<5%)"
MY_ADDITIONS = "My additions"


def saved_additions(build: vdf.VDFDict) -> list[str]:
    """Items from the guide's "My additions" category, which is kept between runs."""
    try:
        return build["guidedata"]["ItemBuild"]["Items"][MY_ADDITIONS].get_all_for("item")
    except KeyError:
        return []


def categorize_items(
    item_overview: api_schemas.ItemOverview,
    early_match_items: list[int],
    role: const.Role,
    item_names: dict[int, str],
    my_additions: list[str],
) -> dict[str, list[str]]:
    """Sort D2PT meta items into guide categories (category name -> `item_*` names, in order).

    `early_match_items` are the `MATCH_ITEMS` to add to "Early" (see `common_match_items` and `common_shared_items`).
    `item_names` maps item IDs to Valve item names (`1: "item_blink"`).
    """
    meta = f"Meta: {role.name}"
    categories: dict[str, list[str]] = {
        "Consumables": list(const.CONSUMABLES),
        EARLY: ["item_boots"],  # Boots are always there;
        meta: [],
        LOW_PERCENT: [],
        MY_ADDITIONS: list(my_additions),
    }

    def append_item(category: str, item_id: int) -> None:
        item_name = item_names.get(item_id)
        if item_name is None:
            # Can happen right after a patch if D2PT knows new items before Valve's datafeed does;
            logger.warning("❓ Unknown item id {} (not in the dota2.com item list) - skipping.", item_id)
            return
        if item_name not in categories[category]:
            categories[category].append(item_name)

    for item in item_overview["overviewRows"]:
        purchase_rate = item["hero_purchase_rate"]
        if purchase_rate > EARLY_MIN_PURCHASE_RATE and item["best_order"]["avg_minute"] < EARLY_MAX_AVG_MINUTE:
            append_item(EARLY, item["item_id"])
        elif purchase_rate < IGNORE_MAX_PURCHASE_RATE:
            continue
        elif purchase_rate < LOW_PERCENT_MAX_PURCHASE_RATE:
            append_item(LOW_PERCENT, item["item_id"])
        else:
            append_item(meta, item["item_id"])

    for item_id in early_match_items:
        append_item(EARLY, item_id)

    return categories


def common_match_items(hero_matches: api_schemas.Matches) -> list[int]:
    """IDs of `MATCH_ITEMS` bought in at least `MATCH_ITEMS_MIN_SHARE` of the matches, most common first."""
    if not hero_matches:
        return []
    # Count each item once per match, so i.e. two wraith bands in one match don't count twice;
    matches_with_item = Counter(
        item_id
        for match in hero_matches
        for item_id in {item["item_id"] for item in match["data"]["items"]}
        if item_id in MATCH_ITEMS
    )
    return [
        item_id for item_id, count in matches_with_item.most_common() if count / len(hero_matches) >= MATCH_ITEMS_MIN_SHARE
    ]


def common_shared_items(shares: dict[int, float]) -> list[int]:
    """IDs of `MATCH_ITEMS` bought in at least `MATCH_ITEMS_MIN_SHARE` of matches (item ID -> share), most common first."""
    common = [
        (share, item_id) for item_id, share in shares.items() if item_id in MATCH_ITEMS and share >= MATCH_ITEMS_MIN_SHARE
    ]
    return [item_id for _, item_id in sorted(common, reverse=True)]


def current_categories(build: vdf.VDFDict) -> dict[str, list[str]]:
    """The guide's item build as it is now: category name -> `item_*` names, in order."""
    try:
        items = build["guidedata"]["ItemBuild"]["Items"]
    except KeyError:
        return {}
    return {category: items[category].get_all_for("item") for category in items}


def describe_changes(old: dict[str, list[str]], new: dict[str, list[str]]) -> list[str]:
    """One line per category whose items change, i.e. `Early: +magic_wand -bracer`."""
    lines: list[str] = []
    for category in dict.fromkeys([*new, *old]):  # new order first, then categories that disappear
        before, after = old.get(category, []), new.get(category, [])
        added = [f"+{item.removeprefix('item_')}" for item in after if item not in before]
        removed = [f"-{item.removeprefix('item_')}" for item in before if item not in after]
        if added or removed:
            lines.append(f"{category}: {' '.join(added + removed)}")
    return lines


def write_categories(build: vdf.VDFDict, categories: dict[str, list[str]], gameplay_version: str) -> None:
    """Replace the guide's item build with `categories` and stamp the title with today's date and the patch."""
    today = dt.datetime.now(tz=dt.UTC).strftime("%d %b %y")
    build["guidedata"][0, "Title"] = f"Updated: {today}; {gameplay_version}"

    items = vdf.VDFDict([
        (category, vdf.VDFDict([("item", item) for item in names])) for category, names in categories.items()
    ])
    build["guidedata"]["ItemBuild"][0, "Items"] = items
