"""Find, create, load and save Dota 2 hero guide (`.build`) files.

Guide files live in `Steam/userdata/<friend id>/570/remote/guides` and are named `<hero slug>_<unix time>.build`,
i.e. `drow_ranger_1639001733.build`.
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

import vdf

if TYPE_CHECKING:
    import pathlib

__all__ = (
    "find_guide",
    "guide_hero_slug",
    "load_guide",
    "new_guide",
    "new_guide_path",
    "save_guide",
)

GUIDE_SUFFIX = ".build"


def _hex64(number: int) -> str:
    """Format a number the way guide files store IDs and timestamps, i.e. `0x000000005FFA9B3F`."""
    return f"0x{number:016X}"


def guide_hero_slug(path: pathlib.Path) -> str:
    """Hero slug a guide file belongs to, from its file name (`""` for guides without a hero)."""
    return path.stem.rpartition("_")[0]


def find_guide(guides: pathlib.Path, hero_slug: str) -> pathlib.Path | None:
    """Find the guide file for the hero in the `guides` folder, if there is one."""
    if not guides.is_dir():
        return None
    for path in sorted(guides.iterdir()):
        if path.suffix == GUIDE_SUFFIX and guide_hero_slug(path) == hero_slug:
            return path
    return None


def new_guide(
    hero_slug: str,
    *,
    friend_id: int,
    gameplay_version: str,
    now: dt.datetime | None = None,
) -> vdf.VDFDict:
    """Build the contents of an empty guide, matching the files the Dota 2 client creates."""
    now = now or dt.datetime.now(tz=dt.UTC)
    return vdf.VDFDict([
        (
            "guidedata",
            vdf.VDFDict([
                ("Hero", hero_slug),
                ("Title", ""),
                ("GameplayVersion", gameplay_version),
                ("Overview", ""),
                ("GuideRevision", "1"),
                ("AssociatedWorkshopItemID", _hex64(0)),
                ("OriginalCreatorID", _hex64(friend_id)),
                ("GuideFormatVersion", "2"),
                ("TimeUpdated", _hex64(int(now.timestamp()))),
                ("TimePublished", _hex64(0)),
                (
                    "ItemBuild",
                    vdf.VDFDict([
                        ("Items", vdf.VDFDict()),
                        ("ItemTooltips", vdf.VDFDict()),
                    ]),
                ),
            ]),
        ),
    ])


def new_guide_path(guides: pathlib.Path, hero_slug: str, now: dt.datetime | None = None) -> pathlib.Path:
    """File name the Dota 2 client would give a new guide for the hero."""
    now = now or dt.datetime.now(tz=dt.UTC)
    return guides / f"{hero_slug}_{int(now.timestamp())}{GUIDE_SUFFIX}"


def load_guide(path: pathlib.Path) -> vdf.VDFDict:
    """Parse a guide file, keeping duplicate keys (guides repeat `"item"` keys)."""
    with path.open(encoding="utf-8") as f:
        return vdf.parse(f, mapper=vdf.VDFDict)


def save_guide(guide: vdf.VDFDict, path: pathlib.Path) -> None:
    """Write a guide file."""
    with path.open("w", encoding="utf-8") as f:
        vdf.dump(guide, f, pretty=True)
