from __future__ import annotations

from typing import NamedTuple


class ResolutionConst(NamedTuple):
    refresh_button: tuple[int, int]
    progress_tab: tuple[int, int]
    challenges_region: tuple[int, int, int, int]


RESOLUTION_1920_1080 = ResolutionConst(
    refresh_button=(610, 842),
    progress_tab=(729, 88),
    challenges_region=(314, 408, 108, 334),
)

RESOLUTION_MAPPING: dict[str, ResolutionConst] = {
    "1920_1080": RESOLUTION_1920_1080,
}
