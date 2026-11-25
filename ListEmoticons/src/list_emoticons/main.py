"""Extract Dota 2 emoticons into gifs and list them in `index.md` (published with GitHub Pages).

Needs Source 2 Viewer CLI (https://s2v.app/) to convert Valve's textures:
set its path under `[list_emoticons]` in config.toml.

Reads the emoticons from the local Dota 2 install, or with `--from-steam` straight from Steam's content servers
(that needs a Steam account with Dota 2 in its library and Steam Guard turned off).
"""

from __future__ import annotations

import asyncio
import datetime as dt
import itertools
import os
import pathlib
import shutil
import subprocess  # ruff: ignore[suspicious-subprocess-import]
from typing import TYPE_CHECKING, TypedDict

import click
import steam
import vdf
from PIL import Image

from dota2utils_common import Dota2UtilsError, config
from dota2utils_common.logs import logger, setup_logging

from .vpk_files import LocalVPK, SteamVPK, steam_login

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any

    from .vpk_files import VPKFiles

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
VTEX_DIR = TEMP_DIR / "cache_vtex"
PNG_DIR = TEMP_DIR / "cache_png"
# The page lives in the GitHub Pages folder: docs/ListEmoticons/ -> aluerie.github.io/Dota2Utils/ListEmoticons/
PAGE_DIR = TOOL_DIR.parent / "docs" / "ListEmoticons"
GIFS_DIR = PAGE_DIR / "gifs"
INDEX_FILE = PAGE_DIR / "index.md"

DEFINITIONS_FILE = "scripts/emoticons_definitions.txt"
# Where `--from-steam` looks for the Steam login: these environment variables (CI), then config.toml;
USERNAME_ENV = "STEAM_USERNAME"
PASSWORD_ENV = "STEAM_PASSWORD"  # ruff: ignore[hardcoded-password-string] - a variable name

FRAME_SIZE = 32  # emoticon sprite sheets are rows of 32x32 frames;
OUT_SIZE = 96
DEFAULT_MS_PER_FRAME = 100  # if an emoticon's definition has no `ms_per_frame` (almost all are 100);
ALPHA_CUTOFF = 128  # pixels at least this opaque stay visible in the gif;
TRANSPARENT_INDEX = 255  # palette slot for transparent pixels; the other 255 slots hold the frame's colors;
CELLS_PER_ROW = 3
TABLE_HEADER = (
    "| preview | chr | alias | preview | chr | alias | preview | chr | alias |\n"
    "| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
)
INDEX_TABLE_HEADING = "## Table of Dota 2 Emoticons"


def gif_name(emote_id: str) -> str:
    return f"{int(emote_id):0>3d}.gif"


def texture_path(emote: EmoteDict) -> str:
    """Path of the emoticon's sprite sheet texture inside the VPK."""
    return f"panorama/images/emoticons/{emote['image_name'].replace('.', '_')}.vtex_c"


def tool_path(key: str) -> pathlib.Path:
    """Path to an external tool from `[list_emoticons]` in config.toml, checked to exist."""
    path = pathlib.Path(config.require("list_emoticons", key))
    if not path.is_file():
        msg = f"`{key}` in config.toml points to a file that does not exist: {path}"
        raise Dota2UtilsError(msg)
    return path


async def load_definitions(files: VPKFiles) -> dict[str, EmoticonsCategory]:
    """Emoticon categories with their emoticons, from Valve's definition files."""
    definitions = (await files.read_many([DEFINITIONS_FILE])).get(DEFINITIONS_FILE)
    if definitions is None:
        msg = f"{DEFINITIONS_FILE} not found in the Dota 2 files."
        raise Dota2UtilsError(msg)
    category_paths: dict[str, str] = vdf.loads(definitions.decode("utf-8"))["emoticons_definitions"]

    contents = await files.read_many(category_paths.values())
    data: dict[str, EmoticonsCategory] = {}
    for name, path in category_paths.items():
        if path not in contents:
            logger.warning("❓ Missing in VPK: {}", path)
            continue
        utf = "utf-16le" if name == "default" else "utf-8"  # imagine using utf-16le for just one old file :c
        emoticons = vdf.loads(contents[path].decode(utf))["emoticons"]
        data[name] = {"utf": utf, "path": path, "emoticons": emoticons}
    return data


def missing_gifs(data: dict[str, EmoticonsCategory]) -> dict[str, list[EmoteDict]]:
    """Category -> emoticons that don't have a gif in the `gifs` folder yet."""
    missing: dict[str, list[EmoteDict]] = {}
    for name, category in data.items():
        emotes = [
            emote for emote_id, emote in category["emoticons"].items() if not (GIFS_DIR / gif_name(emote_id)).is_file()
        ]
        if emotes:
            missing[name] = emotes
    return missing


async def extract_textures(files: VPKFiles, missing: dict[str, list[EmoteDict]]) -> None:
    """Save the `.vtex_c` textures of `missing` emoticons into the cache, one folder per category."""
    # Start clean, so Source 2 Viewer only converts what's needed this run;
    shutil.rmtree(VTEX_DIR, ignore_errors=True)
    shutil.rmtree(PNG_DIR, ignore_errors=True)

    contents = await files.read_many(texture_path(emote) for emotes in missing.values() for emote in emotes)
    for name, emotes in missing.items():
        for emote in emotes:
            path = texture_path(emote)
            if path not in contents:
                logger.warning("❓ Missing in VPK: {}", path)
                continue
            save_path = VTEX_DIR / name / path.rsplit("/", 1)[-1]
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_bytes(contents[path])


def decompile_vtex_c_into_png_series() -> None:
    """Convert the cached `.vtex_c` textures into `.png` sprite sheets with Source 2 Viewer."""
    PNG_DIR.mkdir(parents=True, exist_ok=True)
    # It prints a few lines per texture (thousands in total) - keep them out of the console unless it fails;
    result = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [str(tool_path("source2_viewer_cli")), "-i", str(VTEX_DIR), "-o", str(PNG_DIR), "--recursive"],
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


def make_gif(sprite_sheet: pathlib.Path, out_path: pathlib.Path, ms_per_frame: int = DEFAULT_MS_PER_FRAME) -> None:
    """Split a sprite sheet into upscaled frames and save them as a looping gif."""
    with Image.open(sprite_sheet) as im:
        sheet = im.convert("RGBA")
    frames = [
        gif_frame(sheet.crop((i * FRAME_SIZE, 0, (i + 1) * FRAME_SIZE, FRAME_SIZE)))
        for i in range(sheet.width // FRAME_SIZE)
    ]
    if not frames:
        msg = f"Sprite sheet is narrower than one {FRAME_SIZE}px frame: {sprite_sheet}"
        raise Dota2UtilsError(msg)

    # The transparent slot gets one color that no frame uses. Pillow crops `disposal=2` frames to where they differ
    # from that slot's color, so a color that real pixels have (i.e. black) would cut those pixels off;
    used = {color for frame in frames for color in palette_colors(frame)}
    transparent_color = next(
        (r, g, b) for r in range(256) for g in (255, 0, 128) for b in (255, 0, 128) if (r, g, b) not in used
    )
    for frame in frames:
        palette = (frame.getpalette() or [])[: 3 * TRANSPARENT_INDEX]
        palette += [0] * (3 * TRANSPARENT_INDEX - len(palette))
        frame.putpalette([*palette, *transparent_color])

    # `disposal=2` clears each frame before the next one, so transparent parts don't keep the old frame's pixels;
    # `optimize=False` keeps the palettes as they are, so the transparent slot stays where we put it;
    frames[0].save(
        out_path,
        save_all=True,
        append_images=frames[1:],
        duration=ms_per_frame,
        loop=0,
        disposal=2,
        transparency=TRANSPARENT_INDEX,
        optimize=False,
    )


def gif_frame(frame: Image.Image) -> Image.Image:
    """Convert an RGBA frame into an upscaled frame of up to 255 colors, with `TRANSPARENT_INDEX` for transparent pixels."""
    # GIF pixels are either fully transparent or fully opaque. Cut soft edges at 50% alpha (like ImageMagick does),
    # otherwise every barely visible edge pixel would turn solid;
    visible = frame.getchannel("A").point(lambda alpha: 255 if alpha >= ALPHA_CUTOFF else 0)
    rgb = Image.new("RGB", frame.size)
    rgb.paste(frame.convert("RGB"), mask=visible)
    # Frames often have more than 256 colors; "max coverage" keeps them closest to the original
    # (closer than ImageMagick did), and one palette slot stays free for transparency;
    paletted = rgb.quantize(colors=TRANSPARENT_INDEX, method=Image.Quantize.MAXCOVERAGE)
    paletted.paste(TRANSPARENT_INDEX, mask=visible.point(lambda alpha: 255 - alpha))
    paletted.info["transparency"] = TRANSPARENT_INDEX
    return paletted.resize((OUT_SIZE, OUT_SIZE), Image.Resampling.NEAREST)


def palette_colors(frame: Image.Image) -> set[tuple[int, ...]]:
    """Colors of the palette slots that the frame's visible pixels use."""
    palette = frame.getpalette() or []
    return {
        tuple(palette[3 * index : 3 * index + 3])
        for count, index in zip(frame.histogram(), range(256), strict=True)
        if count and index != TRANSPARENT_INDEX
    }


def generate_gifs(data: dict[str, EmoticonsCategory]) -> int:
    """Create the gifs that are missing from the `gifs` folder (from the converted sprite sheets); return how many."""
    GIFS_DIR.mkdir(parents=True, exist_ok=True)
    created = 0
    for name, category in data.items():
        for emote_id, emote in category["emoticons"].items():
            out_path = GIFS_DIR / gif_name(emote_id)
            sprite_sheet = PNG_DIR / name / f"{emote['image_name'].replace('.', '_')}.png"
            if not out_path.is_file() and sprite_sheet.is_file():
                make_gif(sprite_sheet, out_path, int(emote.get("ms_per_frame") or DEFAULT_MS_PER_FRAME))
                created += 1
    return created


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


def build_index(tables: str, emotes_total: int, today: dt.date | None = None) -> bool:
    """Replace everything after the "Table of Dota 2 Emoticons" heading in `index.md` with fresh stats and tables.

    Leaves the file alone (and returns `False`) if the tables didn't change, so the "Last Updated" date
    only moves when something new shows up.
    """
    text = INDEX_FILE.read_text(encoding="utf-8")
    intro, heading, old_body = text.partition(INDEX_TABLE_HEADING)
    if not heading:
        msg = f'"{INDEX_TABLE_HEADING}" heading not found in {INDEX_FILE}'
        raise Dota2UtilsError(msg)
    if old_body.endswith(f"</table>\n\n{tables}"):
        return False

    today = today or dt.datetime.now(tz=dt.UTC).date()
    stats = (
        "\n<table>\n"
        f"    <tr><td>Last Updated</td><td>{today.strftime('%d/%B/%Y')}</td></tr>\n"
        f"    <tr><td>Amount of emoticons listed</td><td>{emotes_total}</td></tr>\n"
        "</table>\n\n"
    )
    INDEX_FILE.write_text(f"{intro}{INDEX_TABLE_HEADING}\n{stats}{tables}", encoding="utf-8", newline="\n")
    return True


async def update(files: VPKFiles) -> None:
    """Create gifs for new emoticons and rebuild `index.md`, reading the Dota 2 files from `files`."""
    logger.info("📦 Reading emoticon definitions")
    data = await load_definitions(files)

    missing = missing_gifs(data)
    if missing:
        logger.info("📦 Extracting textures of {} new emoticons", sum(len(emotes) for emotes in missing.values()))
        await extract_textures(files, missing)
        logger.info("🔧 Converting textures to PNG with Source 2 Viewer")
        decompile_vtex_c_into_png_series()
        logger.info("🎬 Created {} gifs", generate_gifs(data))
    else:
        logger.info("✨ Every emoticon already has a gif")

    tables, total = render_tables(data)
    if build_index(tables, total):
        logger.success("💖💖💖 Done! index.md updated: {} emoticons listed. 💖💖💖", total)
    else:
        logger.success("💖 Done! No new emoticons - index.md is already up to date ({} emoticons).", total)


def steam_credentials() -> dict[str, str]:
    """Login of the Steam account for `--from-steam`: from the environment (CI), else from config.toml."""
    settings = config.section("list_emoticons")
    username = os.environ.get(USERNAME_ENV) or settings.get("steam_username")
    password = os.environ.get(PASSWORD_ENV) or settings.get("steam_password")
    if not username or not password:
        msg = (
            f"`--from-steam` needs a Steam login: set the {USERNAME_ENV} and {PASSWORD_ENV} environment variables, "
            "or `steam_username` and `steam_password` under `[list_emoticons]` in config.toml."
        )
        raise Dota2UtilsError(msg)
    return {"username": username, "password": password}


async def update_from_steam() -> None:
    """`update` with the Dota 2 files downloaded from Steam."""
    try:
        async with steam_login(**steam_credentials()) as client:
            logger.info("🔑 Logged into Steam")
            await update(await SteamVPK.fetch(client, TEMP_DIR))
    except steam.LoginError as exc:
        msg = f"Steam login failed ({exc}). Check the username and password."
        raise Dota2UtilsError(msg) from exc
    except EOFError as exc:
        # steam.py asks for a Steam Guard code on the console, and there's nobody to answer in CI;
        msg = "Steam asked for a Steam Guard code. `--from-steam` needs an account with Steam Guard turned off."
        raise Dota2UtilsError(msg) from exc


def run_cli(coroutine: Coroutine[Any, Any, None]) -> None:
    """Run `coroutine`, printing our errors as plain messages."""
    try:
        asyncio.run(coroutine)
    except Dota2UtilsError as exc:
        logger.error(str(exc))
        raise SystemExit(1) from exc


@click.group(invoke_without_command=True)
@click.option(
    "--from-steam",
    is_flag=True,
    help="Download the Dota 2 files from Steam (needs a Steam login) instead of reading the local install.",
)
@click.pass_context
def cli(ctx: click.Context, *, from_steam: bool) -> None:
    """Create gifs for new Dota 2 emoticons and rebuild the emoticons page."""
    setup_logging()
    if ctx.invoked_subcommand is None:
        run_cli(update_from_steam() if from_steam else update(LocalVPK.from_dota_install()))
