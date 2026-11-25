"""Shared pytest fixtures: every test runs without the real `config.toml` and without network access."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import requests

from dota2utils_common import config

if TYPE_CHECKING:
    import pathlib
    from collections.abc import Iterator


@pytest.fixture(autouse=True)
def isolated_config(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[pathlib.Path]:
    """Point the config at a (not yet existing) file in the test's temp folder; write to it to set config."""
    path = tmp_path / "config.toml"
    monkeypatch.setenv("DOTA2UTILS_CONFIG", str(path))
    config.load_config.cache_clear()
    yield path
    config.load_config.cache_clear()


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*_args: object, **_kwargs: object) -> None:
        msg = "Tests must not use the network"
        raise RuntimeError(msg)

    monkeypatch.setattr(requests, "get", blocked)
