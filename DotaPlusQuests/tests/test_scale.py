from __future__ import annotations

from dota_plus_quests.main import NEXT_HERO, PROGRESS_TAB, REFRESH_BUTTON, Point, scale


def test_scale_identity_on_base_resolution() -> None:
    assert scale(REFRESH_BUTTON, (2560, 1440)) == REFRESH_BUTTON


def test_scale_to_1080p_matches_old_measurements() -> None:
    # Measured by hand on 1920x1080 in the old version of the script (within a few pixels; the UI moved slightly since).
    old_1080p = {PROGRESS_TAB: Point(729, 88), REFRESH_BUTTON: Point(610, 842), NEXT_HERO: Point(1817, 86)}
    for point, old in old_1080p.items():
        scaled = scale(point, (1920, 1080))
        assert abs(scaled.x - old.x) <= 15
        assert abs(scaled.y - old.y) <= 15
