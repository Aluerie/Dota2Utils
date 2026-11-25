"""Extract Dota 2 emoticons into gifs and list them in `index.md` (published with GitHub Pages).

Needs two external tools, set their paths under `[list_emoticons]` in config.toml:

* Source 2 Viewer CLI - https://s2v.app/
* ImageMagick - https://imagemagick.org/script/download.php

If Dota 2 is not installed, the emoticon files can still be downloaded with `steamctl`
(https://github.com/ValvePython/steamctl):

```ps1
steamctl depot download -a 570 --vpk -n '*pak01_dir*:*emoticons.txt' -nd -o ./.temp/
steamctl depot download -a 570 --vpk -n '*pak01_dir*:*emoticons/*.vtex_c' -nd -o ./.temp/cache_vtex_c
```
"""

from __future__ import annotations

import datetime as dt
import itertools
import pathlib
import subprocess  # ruff: ignore[suspicious-subprocess-import]
from typing import TYPE_CHECKING, TypedDict

import vdf
import vpk
from PIL import Image

from dota2utils_common import Dota2UtilsError, config, steam
from dota2utils_common.logs import logger, setup_logging

if TYPE_CHECKING:

    class EmoteDict(TypedDict):
        image_name: str
        ms_per_frame: str
        aliases: dict[str, str]

    class EmoticonsCategory(TypedDict):
        utf: str
        path: str
        emoticons: dict[str, EmoteDict]


# ListEmoticons/src/list_emoticons/main.py -> ListEmoticons/
TOOL_DIR = pathlib.Path(__file__).resolve().parents[2]
TEMP_DIR = TOOL_DIR / ".temp"
# The page lives in the GitHub Pages folder: docs/ListEmoticons/ -> aluerie.github.io/Dota2Utils/ListEmoticons/
PAGE_DIR = TOOL_DIR.parent / "docs" / "ListEmoticons"
GIFS_DIR = PAGE_DIR / "gifs"
INDEX_FILE = PAGE_DIR / "index.md"

FRAME_SIZE = 32  # emoticon sprite sheets are rows of 32x32 frames;
OUT_SIZE = 96
CELLS_PER_ROW = 3
TABLE_HEADER = (
    "| preview | chr | alias | preview | chr | alias | preview | chr | alias |\n"
    "| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
)
INDEX_TABLE_HEADING = "## Table of Dota 2 Emoticons"


def gif_name(emote_id: str) -> str:
    return f"{int(emote_id):0>3d}.gif"


def tool_path(key: str) -> pathlib.Path:
    """Path to an external tool from `[list_emoticons]` in config.toml, checked to exist."""
    path = pathlib.Path(config.require("list_emoticons", key))
    if not path.is_file():
        msg = f"`{key}` in config.toml points to a file that does not exist: {path}"
        raise Dota2UtilsError(msg)
    return path


def import_vtex_c_files() -> dict[str, EmoticonsCategory]:
    """Read emoticon definitions from the Dota 2 VPK and extract their `.vtex_c` textures into the cache."""
    pak1 = vpk.open(str(steam.dota_path() / "game" / "dota" / "pak01_dir.vpk"))

    emoticons_definitions = vdf.loads(pak1["scripts/emoticons_definitions.txt"].read().decode("utf-8"))

    data: dict[str, EmoticonsCategory] = {}
    for emote_name, vdf_path in emoticons_definitions["emoticons_definitions"].items():
        utf = "utf-16le" if emote_name == "default" else "utf-8"  # imagine using utf-16le for just one old file :c
        emoticons = vdf.loads(pak1[vdf_path].read().decode(utf))["emoticons"]
        data[emote_name] = {"utf": utf, "path": vdf_path, "emoticons": emoticons}

    for emote_name, category in data.items():
        cache_path = TEMP_DIR / "cache_vtex" / emote_name
        for value in category["emoticons"].values():
            emote_filename = value["image_name"].replace(".", "_") + ".vtex_c"
            emoticon_path = f"panorama/images/emoticons/{emote_filename}"
            save_path = cache_path / emote_filename
            save_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                pak1[emoticon_path].save(str(save_path))
            except KeyError:
                logger.warning("❓ Missing in VPK: {}", emoticon_path)

    return data


def decompile_vtex_c_into_png_series() -> None:
    """Convert the cached `.vtex_c` textures into `.png` sprite sheets with Source 2 Viewer."""
    out = TEMP_DIR / "cache_png"
    out.mkdir(parents=True, exist_ok=True)
    # It prints a few lines per texture (thousands in total) - keep them out of the console unless it fails;
    result = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [str(tool_path("source2_viewer_cli")), "-i", str(TEMP_DIR / "cache_vtex"), "-o", str(out), "--recursive"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        tail = "\n".join((result.stderr or result.stdout).strip().splitlines()[-15:])
        msg = f"Source 2 Viewer failed (exit code {result.returncode}). Last lines of its output:\n{tail}"
        raise Dota2UtilsError(msg)


def clear_frames() -> None:
    """Delete frame `.png`s from the temp folder, so frames of a longer previous gif don't leak into the next one."""
    for frame in TEMP_DIR.glob("*.png"):
        frame.unlink()


def make_gif(sprite_sheet: pathlib.Path, out_path: pathlib.Path, magick: pathlib.Path) -> None:
    """Split a sprite sheet into upscaled frames and combine them into a looping gif with ImageMagick."""
    clear_frames()
    with Image.open(sprite_sheet) as im:
        for i in range(im.size[0] // FRAME_SIZE):
            frame = im.crop((i * FRAME_SIZE, 0, (i + 1) * FRAME_SIZE, FRAME_SIZE))
            frame.resize((OUT_SIZE, OUT_SIZE), Image.Resampling.NEAREST).save(TEMP_DIR / f"{i:0>3d}.png")
    # ImageMagick expands the `*.png` glob itself; frames are zero-padded so they sort correctly.
    subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [str(magick), "-loop", "0", "-delay", "10", "-dispose", "background", str(TEMP_DIR / "*.png"), str(out_path)],
        check=True,
    )


def generate_gifs(data: dict[str, EmoticonsCategory]) -> None:
    """Create the gifs that are missing from the `gifs` folder."""
    GIFS_DIR.mkdir(parents=True, exist_ok=True)
    magick = tool_path("image_magick")
    for name, category in data.items():
        for emote_id, emote in category["emoticons"].items():
            out_path = GIFS_DIR / gif_name(emote_id)
            if not out_path.is_file():
                sprite_sheet = TEMP_DIR / "cache_png" / name / f"{emote['image_name'].replace('.', '_')}.png"
                make_gif(sprite_sheet, out_path, magick)
    clear_frames()


def render_tables(data: dict[str, EmoticonsCategory]) -> tuple[str, int]:
    """Markdown tables (one per emoticon category, three emoticons per row) and the total number of emoticons."""
    markdown = ""
    total = 0
    for name, category in data.items():
        markdown += f"## {name.capitalize()}\n\n{TABLE_HEADER}"
        cells = [
            f"| ![emoticon](./gifs/{gif_name(emote_id)}) | {chr(0xE000 + int(emote_id)):s} | `:{emote['aliases']['0']:s}:` "
            for emote_id, emote in category["emoticons"].items()
        ]
        for row in itertools.batched(cells, CELLS_PER_ROW, strict=False):
            markdown += "".join(row) + "|\n"
        markdown += "\n"
        total += len(cells)
    return markdown, total


def build_index(tables: str, emotes_total: int, today: dt.date | None = None) -> None:
    """Replace everything after the "Table of Dota 2 Emoticons" heading in `index.md` with fresh stats and tables."""
    today = today or dt.datetime.now(tz=dt.UTC).date()
    stats = (
        "\n<table>\n"
        f"    <tr><td>Last Updated</td><td>{today.strftime('%d/%B/%Y')}</td></tr>\n"
        f"    <tr><td>Amount of emoticons listed</td><td>{emotes_total}</td></tr>\n"
        "</table>\n\n"
    )
    text = INDEX_FILE.read_text(encoding="utf-8")
    intro, heading, _ = text.partition(INDEX_TABLE_HEADING)
    if not heading:
        msg = f'"{INDEX_TABLE_HEADING}" heading not found in {INDEX_FILE}'
        raise Dota2UtilsError(msg)
    INDEX_FILE.write_text(f"{intro}{INDEX_TABLE_HEADING}\n{stats}{tables}", encoding="utf-8", newline="\n")


def run() -> None:
    """Extract emoticons from Dota 2, create missing gifs and rebuild `index.md`."""
    logger.info("📦 Extracting emoticons from the Dota 2 files")
    data = import_vtex_c_files()
    logger.info("🔧 Converting textures to PNG with Source 2 Viewer")
    decompile_vtex_c_into_png_series()
    logger.info("🎬 Creating missing gifs with ImageMagick")
    generate_gifs(data)
    logger.info("📄 Rebuilding index.md")
    tables, total = render_tables(data)
    build_index(tables, total)
    logger.success("💖💖💖 Done! {} emoticons listed. 💖💖💖", total)


def main() -> None:
    """Update the emoticon list, printing problems as plain messages."""
    setup_logging()
    try:
        run()
    except Dota2UtilsError as exc:
        logger.error(str(exc))
        raise SystemExit(1) from exc
