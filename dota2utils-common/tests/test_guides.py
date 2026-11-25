from __future__ import annotations

import datetime as dt
import pathlib

from dota2utils_common import guides

NOW = dt.datetime(2026, 11, 24, 12, 0, tzinfo=dt.UTC)


def test_guide_hero_slug() -> None:
    assert guides.guide_hero_slug(pathlib.Path("drow_ranger_1639001733.build")) == "drow_ranger"
    assert not guides.guide_hero_slug(pathlib.Path("_1610259263.build"))


def test_find_guide_matches_whole_slug(tmp_path: pathlib.Path) -> None:
    for name in ("_1610259263.build", "lina_1610278905.build", "lion_1610278906.build", "upconverted2.txt"):
        (tmp_path / name).touch()
    assert guides.find_guide(tmp_path, "lina") == tmp_path / "lina_1610278905.build"
    assert guides.find_guide(tmp_path, "lin") is None
    assert guides.find_guide(tmp_path / "missing", "lina") is None


def test_new_guide_round_trip(tmp_path: pathlib.Path) -> None:
    path = guides.new_guide_path(tmp_path, "crystal_maiden", NOW)
    assert path.name == f"crystal_maiden_{int(NOW.timestamp())}.build"

    guide = guides.new_guide("crystal_maiden", friend_id=112636165, gameplay_version="7.41e", now=NOW)
    guides.save_guide(guide, path)
    loaded = guides.load_guide(path)["guidedata"]

    assert loaded["Hero"] == "crystal_maiden"
    assert loaded["GameplayVersion"] == "7.41e"
    assert loaded["OriginalCreatorID"] == "0x0000000006B6B105"
    assert loaded["TimeUpdated"] == f"0x{int(NOW.timestamp()):016X}"
    assert list(loaded["ItemBuild"].keys()) == ["Items", "ItemTooltips"]
    assert guides.find_guide(tmp_path, "crystal_maiden") == path
