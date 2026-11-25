from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from dota2utils_common import ConfigError, config

if TYPE_CHECKING:
    import pathlib


def test_missing_config_file_is_empty() -> None:
    assert config.load_config() == {}
    assert config.section("steam") == {}


def test_reads_sections(isolated_config: pathlib.Path) -> None:
    isolated_config.write_text('[steam]\nfriend_id = 42\nusername = "me"\n', encoding="utf-8")
    assert config.section("steam") == {"friend_id": 42, "username": "me"}
    assert config.require("steam", "username") == "me"


@pytest.mark.parametrize("content", ["", "[steam]\n", '[steam]\nusername = ""\n', '[steam]\nusername = "  "\n'])
def test_require_missing_value(isolated_config: pathlib.Path, content: str) -> None:
    isolated_config.write_text(content, encoding="utf-8")
    with pytest.raises(ConfigError, match=r"Set `username` under `\[steam\]`"):
        config.require("steam", "username")


def test_section_must_be_a_table(isolated_config: pathlib.Path) -> None:
    isolated_config.write_text('steam = "oops"\n', encoding="utf-8")
    with pytest.raises(ConfigError, match="must be a table"):
        config.section("steam")


def test_invalid_toml(isolated_config: pathlib.Path) -> None:
    isolated_config.write_text("[steam\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="not valid TOML"):
        config.load_config()
