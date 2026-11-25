from __future__ import annotations

import asyncio
import datetime as dt
import itertools
import random
import subprocess
from typing import TYPE_CHECKING, Any

import pytest
from PIL import GifImagePlugin, Image

from dota2utils_common import Dota2UtilsError, config
from list_emoticons import main

if TYPE_CHECKING:
    import pathlib
    from collections.abc import Iterable


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


def test_build_index_keeps_unchanged_tables(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    index = tmp_path / "index.md"
    monkeypatch.setattr(main, "INDEX_FILE", index)
    index.write_text("# Intro\n\n## Table of Dota 2 Emoticons\n", encoding="utf-8")
    assert main.build_index("## Default\ntable\n", 1, today=dt.date(2026, 11, 24))
    before = index.read_bytes()

    # Same tables a day later: the "Last Updated" date must not move;
    assert not main.build_index("## Default\ntable\n", 1, today=dt.date(2026, 11, 25))
    assert index.read_bytes() == before

    assert main.build_index("## Default\ntable\nnew row\n", 2, today=dt.date(2026, 11, 25))
    assert "<td>25/November/2026</td>" in index.read_text(encoding="utf-8")


class FakeFiles:
    def __init__(self, files: dict[str, bytes]) -> None:
        self.files = files
        self.requested: list[str] = []

    async def read_many(self, paths: Iterable[str]) -> dict[str, bytes]:
        paths = list(paths)
        self.requested += paths
        return {path: self.files[path] for path in paths if path in self.files}


def test_extracts_only_textures_of_new_emoticons(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "GIFS_DIR", tmp_path / "gifs")
    monkeypatch.setattr(main, "VTEX_DIR", tmp_path / "vtex")
    monkeypatch.setattr(main, "PNG_DIR", tmp_path / "png")
    (tmp_path / "gifs").mkdir()
    (tmp_path / "gifs" / "001.gif").touch()  # wink already has a gif;
    (tmp_path / "vtex" / "old").mkdir(parents=True)  # leftovers of a previous run get cleared;

    files = FakeFiles({
        "panorama/images/emoticons/blush_png.vtex_c": b"blush texture",
        "panorama/images/emoticons/cheeky_png.vtex_c": b"cheeky texture",
    })
    missing = main.missing_gifs(DATA)
    asyncio.run(main.extract_textures(files, missing))

    assert {emote["image_name"] for emote in missing["default"]} == {"blush.png", "cheeky.png", "cool.png"}
    assert "panorama/images/emoticons/wink_png.vtex_c" not in files.requested
    assert sorted(p.relative_to(tmp_path / "vtex").as_posix() for p in (tmp_path / "vtex").rglob("*.vtex_c")) == [
        "default/blush_png.vtex_c",
        "default/cheeky_png.vtex_c",
    ]  # cool's texture is missing from the VPK - skipped with a warning;
    assert not (tmp_path / "vtex" / "old").exists()


def test_load_definitions() -> None:
    definitions = '"emoticons_definitions"\n{\n"default" "scripts/a.txt"\n"ranked" "scripts/b.txt"\n}\n'
    emoticon = '"emoticons"\n{{\n"{}"\n{{\n"image_name" "{}.png"\n"ms_per_frame" "{}"\n"aliases"\n{{\n"0" "{}"\n}}\n}}\n}}\n'
    files = FakeFiles({
        "scripts/emoticons_definitions.txt": definitions.encode("utf-8"),
        "scripts/a.txt": emoticon.format(1, "wink", 100, "wink").encode("utf-16le"),  # "default" is UTF-16;
        "scripts/b.txt": emoticon.format(9, "rank", 50, "rank").encode("utf-8"),
    })
    data = asyncio.run(main.load_definitions(files))
    assert data["default"]["emoticons"]["1"]["aliases"]["0"] == "wink"
    assert data["ranked"]["emoticons"]["9"]["ms_per_frame"] == "50"


def test_build_index_needs_heading(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    index = tmp_path / "index.md"
    index.write_text("# No table heading\n", encoding="utf-8")
    monkeypatch.setattr(main, "INDEX_FILE", index)
    with pytest.raises(Dota2UtilsError, match="heading not found"):
        main.build_index("", 0)


def test_source2_viewer_failure_shows_its_output(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "PNG_DIR", tmp_path / "png")
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


def test_make_gif(tmp_path: pathlib.Path) -> None:
    # A 3-frame sprite sheet: red, green, blue;
    sheet = Image.new("RGBA", (3 * main.FRAME_SIZE, main.FRAME_SIZE))
    for i, color in enumerate([(255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255)]):
        sheet.paste(color, (i * main.FRAME_SIZE, 0, (i + 1) * main.FRAME_SIZE, main.FRAME_SIZE))
    sheet_path, gif_path = tmp_path / "sheet.png", tmp_path / "out.gif"
    sheet.save(sheet_path)

    main.make_gif(sheet_path, gif_path, ms_per_frame=50)

    with Image.open(gif_path) as gif:
        assert isinstance(gif, GifImagePlugin.GifImageFile)
        assert gif.size == (main.OUT_SIZE, main.OUT_SIZE)
        assert gif.info["loop"] == 0
        frames = []
        for i in range(gif.n_frames):
            gif.seek(i)
            frames.append((gif.info["duration"], gif.disposal_method, gif.convert("RGBA").getpixel((48, 48))))
    # `disposal_method == 2`: each frame is cleared before the next, so transparent pixels don't show the old frame;
    assert frames == [(50, 2, (255, 0, 0, 255)), (50, 2, (0, 255, 0, 255)), (50, 2, (0, 0, 255, 255))]


def decoded_frames(gif_path: pathlib.Path) -> list[Image.Image]:
    with Image.open(gif_path) as gif:
        assert isinstance(gif, GifImagePlugin.GifImageFile)
        frames = []
        for i in range(gif.n_frames):
            gif.seek(i)
            frames.append(gif.convert("RGBA"))
    return frames


def test_make_gif_keeps_black_edges(tmp_path: pathlib.Path) -> None:
    # Regression: Pillow crops `disposal=2` frames to where they differ from the transparent slot's color in the
    # (reordered) first palette. When that came out black, black borders of later frames were cut off.
    # It takes a colorful first frame to get the palette reordered;
    size = main.FRAME_SIZE
    noise = random.Random(1)  # ruff: ignore[suspicious-non-cryptographic-random-usage] - test pixels
    sheet = Image.new("RGBA", (2 * size, size), (0, 0, 0, 0))
    for x, y in itertools.product(range(4, size - 4), repeat=2):
        sheet.putpixel((x, y), (noise.randrange(1, 256), noise.randrange(1, 256), noise.randrange(1, 256), 255))
    sheet.paste((0, 0, 0, 255), (size, 0, 2 * size, size))
    sheet.paste((0, 255, 0, 255), (size + 4, 4, 2 * size - 4, size - 4))
    sheet_path, gif_path = tmp_path / "sheet.png", tmp_path / "out.gif"
    sheet.save(sheet_path)

    main.make_gif(sheet_path, gif_path)

    second = decoded_frames(gif_path)[1]
    assert second.getpixel((0, 0)) == (0, 0, 0, 255)
    assert second.getpixel((95, 95)) == (0, 0, 0, 255)
    assert second.getpixel((48, 48)) == (0, 255, 0, 255)


def test_make_gif_cuts_soft_edges_at_half_alpha(tmp_path: pathlib.Path) -> None:
    size = main.FRAME_SIZE
    sheet = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sheet.paste((255, 0, 0, 100), (0, 0, size // 2, size))  # mostly transparent - dropped;
    sheet.paste((0, 0, 255, 200), (size // 2, 0, size, size))  # mostly opaque - kept;
    sheet_path, gif_path = tmp_path / "sheet.png", tmp_path / "out.gif"
    sheet.save(sheet_path)

    main.make_gif(sheet_path, gif_path)

    (frame,) = decoded_frames(gif_path)
    assert frame.getchannel("A").getpixel((10, 10)) == 0
    assert frame.getpixel((80, 10)) == (0, 0, 255, 255)


def test_make_gif_rejects_tiny_sheet(tmp_path: pathlib.Path) -> None:
    sheet_path = tmp_path / "sheet.png"
    Image.new("RGBA", (10, 10)).save(sheet_path)
    with pytest.raises(Dota2UtilsError, match="narrower"):
        main.make_gif(sheet_path, tmp_path / "out.gif")


def test_steam_credentials(isolated_config: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(main.USERNAME_ENV, raising=False)
    monkeypatch.delenv(main.PASSWORD_ENV, raising=False)
    with pytest.raises(Dota2UtilsError, match="needs a Steam login"):
        main.steam_credentials()

    isolated_config.write_text('[list_emoticons]\nsteam_username = "cfg"\nsteam_password = "cfg pass"\n', encoding="utf-8")
    config.load_config.cache_clear()
    assert main.steam_credentials() == {"username": "cfg", "password": "cfg pass"}

    # The environment (GitHub secrets in CI) wins over config.toml;
    monkeypatch.setenv(main.USERNAME_ENV, "env")
    monkeypatch.setenv(main.PASSWORD_ENV, "env pass")
    assert main.steam_credentials() == {"username": "env", "password": "env pass"}
