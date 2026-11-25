"""Load the repository-wide `config.toml`."""

from __future__ import annotations

import functools
import os
import pathlib
import tomllib
from typing import Any

from .errors import ConfigError

__all__ = (
    "REPO_ROOT",
    "config_path",
    "load_config",
    "require",
    "section",
)

# dota2utils-common/src/dota2utils_common/config.py -> repository root
REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]


def config_path() -> pathlib.Path:
    """Path to `config.toml`; the `DOTA2UTILS_CONFIG` environment variable overrides the default location."""
    if override := os.environ.get("DOTA2UTILS_CONFIG"):
        return pathlib.Path(override)
    return REPO_ROOT / "config.toml"


@functools.cache
def load_config() -> dict[str, Any]:
    """Load `config.toml`, or an empty config if the file does not exist."""
    path = config_path()
    if not path.is_file():
        return {}
    try:
        with path.open("rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        msg = f"{path} is not valid TOML: {exc}"
        raise ConfigError(msg) from exc


def section(name: str) -> dict[str, Any]:
    """Return a top-level `[name]` table of the config, or an empty dict if it is absent."""
    value = load_config().get(name, {})
    if not isinstance(value, dict):
        msg = f"`{name}` in {config_path()} must be a table (`[{name}]`)."
        raise ConfigError(msg)
    return value


def require(section_name: str, key: str) -> Any:
    """Return `[section_name].key` from the config, raising a readable error if it is not set."""
    value = section(section_name).get(key)
    if value is None or (isinstance(value, str) and not value.strip()):
        msg = (
            f"Set `{key}` under `[{section_name}]` in {config_path()} "
            "(copy `config.example.toml` to `config.toml` if you have not yet)."
        )
        raise ConfigError(msg)
    return value
