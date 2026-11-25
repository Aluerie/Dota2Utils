from __future__ import annotations

import datetime as dt
import subprocess
from typing import TYPE_CHECKING, Any

import pytest

from dota2utils_common import Dota2UtilsError
from list_emoticons import main

if TYPE_CHECKING:
    import pathlib


def emote(alias: str) -> dict[str, Any]:
    return {"image_name": f"{alias}.png", "ms_per_frame": "100", "aliases": {"0": alias}}


DATA: Any = {
    "default": {
        "utf": "utf-16le",
        "path": "",
        "emoticons": {"1": emote("wink"), "2": emote("blush"), "3": emote("cheeky"), "4": emote("cool")},
    },
    "empty": {"utf": "utf-8", "path": "", "emoticons": {}},
}


def test_render_tables() -> None:
    tables, total = main.render_tables(DATA)
    assert total == 4
    assert tables == (
        "## Default\n\n"
        f"{main.TABLE_HEADER}"
        "| ![emoticon](./gifs/001.gif) |  | `:wink:` "
        "| ![emoticon](./gifs/002.gif) |  | `:blush:` "
        "| ![emoticon](./gifs/003.gif) |  | `:cheeky:` |\n"
        "| ![emoticon](./gifs/004.gif) |  | `:cool:` |\n"
        "\n"
        "## Empty\n\n"
        f"{main.TABLE_HEADER}"
        "\n"
    )


def test_build_index(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    index = tmp_path / "index.md"
    index.write_text("# Intro\n\n## Table of Dota 2 Emoticons\n\nold stats\n\n## Default\nold table\n", encoding="utf-8")
    monkeypatch.setattr(main, "INDEX_FILE", index)

    main.build_index("## Default\nnew table\n", 1, today=dt.date(2026, 11, 24))

    text = index.read_bytes().decode("utf-8")
    assert text.startswith("# Intro\n\n## Table of Dota 2 Emoticons\n\n<table>\n")
    assert "<td>24/November/2026</td>" in text
    assert text.endswith("</table>\n\n## Default\nnew table\n")
    assert "\r\n" not in text


def test_build_index_needs_heading(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    index = tmp_path / "index.md"
    index.write_text("# No table heading\n", encoding="utf-8")
    monkeypatch.setattr(main, "INDEX_FILE", index)
    with pytest.raises(Dota2UtilsError, match="heading not found"):
        main.build_index("", 0)


def test_source2_viewer_failure_shows_its_output(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "TEMP_DIR", tmp_path)
    monkeypatch.setattr(main, "tool_path", lambda _key: tmp_path / "Source2Viewer-CLI.exe")
    output = "\n".join(f"noise {i}" for i in range(100)) + "\nUnhandled exception: boom"
    monkeypatch.setattr(
        main.subprocess, "run", lambda args, **_kwargs: subprocess.CompletedProcess(args, 1, stdout="", stderr=output)
    )
    with pytest.raises(Dota2UtilsError, match=r"exit code 1\)[\s\S]*Unhandled exception: boom") as error:
        main.decompile_vtex_c_into_png_series()
    assert "noise 0" not in str(error.value)  # only the last lines


def test_page_files_exist() -> None:
    # The page is published from `docs/` - catch the paths drifting away from the real files;
    assert main.INDEX_FILE.is_file()
    assert main.INDEX_TABLE_HEADING in main.INDEX_FILE.read_text(encoding="utf-8")
    assert (main.GIFS_DIR / "001.gif").is_file()
