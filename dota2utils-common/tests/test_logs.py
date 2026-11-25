from __future__ import annotations

from loguru import logger

from dota2utils_common.config import REPO_ROOT
from dota2utils_common.logs import LEVEL_ICONS, setup_logging

# Emoji made from a symbol + this invisible "variation selector" are drawn over the next character in many terminals;
VARIATION_SELECTOR_16 = chr(0xFE0F)


def test_level_icons_are_terminal_friendly() -> None:
    setup_logging()
    for name in LEVEL_ICONS:
        assert VARIATION_SELECTOR_16 not in logger.level(name).icon, name


def test_log_messages_are_terminal_friendly() -> None:
    offenders = [
        f"{path.relative_to(REPO_ROOT)}:{number}"
        for path in REPO_ROOT.glob("*/src/**/*.py")
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if VARIATION_SELECTOR_16 in line
    ]
    assert not offenders, f"Use natively wide emoji (without U+FE0F) in: {offenders}"
