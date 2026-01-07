"""
Docstring for main

Required to download the following tools:

* ImageMagick
    https://imagemagick.org/script/download.php#gsc.tab=0
    and put path tp the portable's `magick.exe` into `IMAGE_MAGICK` global constant.
* Source 2 Viewer CLI utility
    https://s2v.app/
    and put path to the `Source2Viewer-CLI.exe` into `SOURCE2_VIEWER_CLI` global constant.
"""

from __future__ import annotations

import datetime
import logging
import os
import pathlib
from typing import TYPE_CHECKING, TypedDict

import vdf
import vpk
from PIL import Image

from utils import create_dir_if_not_exists

if TYPE_CHECKING:

    class EmoteDict(TypedDict):
        image_name: str
        ms_per_frame: str
        aliases: dict[str, str]

    class EmoticonsCategory(TypedDict):
        utf: str
        path: str
        emoticons: dict[str, EmoteDict]


log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

SOURCE2_VIEWER_CLI = r"D:\DOWNLOADS\cli-windows-x64\Source2Viewer-CLI.exe"
IMAGE_MAGICK = r"D:\DOWNLOADS\ImageMagick-7.1.2-12-portable-Q16-HDRI-x64\magick.exe"

OUT_TEMP = "./.temp"
OUT_DIR = "./gifs"
OUT_SIZE = 96


def import_vtex_c_files() -> dict[str, EmoticonsCategory]:
    """
    Docstring for import_vtex_c_files

    Fancy Off-topic Note
    ----------
    If we don't have Dota 2 installed we can still import vtex files by using steamctl library:
    * pip install steamctl
    * https://pypi.org/project/steamctl/
    * https://github.com/ValvePython/steamctl

    And then get the files via
    ```ps1
    steamctl depot download -a 570 --vpk -n '*pak01_dir*:*emoticons.txt' -nd -o ./.temp/
    steamctl depot download -a 570 --vpk -n '*pak01_dir*:*emoticons/*.vtex_c' -nd -o ./.temp/cache_vtex_c
    ```

    """
    pak1 = vpk.open("C:/Program Files (x86)/Steam/steamapps/common/dota 2 beta/game/dota/pak01_dir.vpk")

    emoticons_definitions = vdf.loads(pak1["scripts/emoticons_definitions.txt"].read().decode("utf-8"))

    data: dict[str, EmoticonsCategory] = {}

    for emote_name, vdf_path in emoticons_definitions["emoticons_definitions"].items():
        utf: str = "utf-16le" if emote_name == "default" else "utf-8"  # imagine using utf-16le for just one old file :c
        temp = vdf.loads(pak1[vdf_path].read().decode(utf))
        temp_emoticons = temp["emoticons"]
        data[emote_name] = {"utf": utf, "path": vdf_path, "emoticons": temp_emoticons}

    create_dir_if_not_exists(OUT_TEMP)
    create_dir_if_not_exists(f"{OUT_TEMP}/cache_vtex")

    for emote_name, category in data.items():
        cache_path = f"{OUT_TEMP}/cache_vtex/{emote_name}"
        create_dir_if_not_exists(cache_path)

        for value in category["emoticons"].values():
            emote_filename = value["image_name"].replace(".", "_") + ".vtex_c"
            emoticon_path = f"panorama/images/emoticons/{emote_filename}"

            try:
                subfolders = emote_filename.rsplit("/", 1)
                if len(subfolders) > 1:
                    pathlib.Path(f"{cache_path}/{subfolders[0]}").mkdir(parents=True)
            except Exception:
                pass  # TODO: Better handling

            try:
                save_path = f"{cache_path}/{emote_filename}"
                pak1[emoticon_path].save(save_path)
            except:
                log.exception("Missing: %s", emoticon_path)

    return data


def decompile_vtex_c_into_png_series() -> None:
    create_dir_if_not_exists(f"{OUT_TEMP}/cache_png")

    os.system(f'{SOURCE2_VIEWER_CLI} -i "{OUT_TEMP}/cache_vtex" -o "{OUT_TEMP}/cache_png" --recursive > NUL')  # noqa: S605


def generate_gifs(data: dict[str, EmoticonsCategory]) -> tuple[str, int]:
    """
    The script creates `.gif`-files that are missing from `gifs` folder.

    It also returns `resp` which presents markdown-tables containing all the emotes.
    """
    create_dir_if_not_exists(OUT_DIR)

    table_headers = """
| preview | chr | alias | preview | chr | alias | preview | chr | alias |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
"""

    def clear_temp_from_pngs_for_gif() -> None:
        """
        Clear temp folder from temp frames.

        We are saving .png frame files into temp but we need to clean it up bcs
        if gif 1 has 40 frames and gif 2 has 30 frames.
        the tool wont remove last 10 frames from previous gif1 by itself.
        """
        for temp_png_frame in pathlib.Path(OUT_TEMP).iterdir():
            if not temp_png_frame.name.endswith(".png"):
                continue
            temp_png_frame.unlink()

    global_counter = 0
    counter = 0

    resp = ""

    for name, category in data.items():
        log.debug("CATEGORY %s", name)
        resp += f"## {name.capitalize()}\n"
        resp += table_headers

        for counter, (k, v) in enumerate(category["emoticons"].items()):
            emote_name = f"{v['image_name'].replace('.', '_')}.png"
            out_path = f"{OUT_DIR}/{int(k):0>3d}.gif"

            # if a gif doesn't exist generate it
            if not pathlib.Path(out_path).is_file():
                clear_temp_from_pngs_for_gif()

                # split the png sequence in separate files
                with pathlib.Path(f"{OUT_TEMP}/cache_png/{name}/{emote_name}").open("rb") as f:
                    im = Image.open(f)
                    for i in range(im.size[0] // 32):
                        im.crop((i * 32, 0, (i + 1) * 32, 32)).resize((OUT_SIZE, OUT_SIZE), Image.Resampling.NEAREST).save(
                            f"{OUT_TEMP}/{i:0>3d}.png"
                        )
                # combines the sequence images into a gif using ImageMagick
                os.system(  # noqa: S605
                    f'{IMAGE_MAGICK} -loop 0 -delay 10 -dispose background "{OUT_TEMP}/*.png" "{out_path}"'
                )  # # -alpha # not sure if we need to mess with it;

            # generate table cells for emoticon
            if counter % 3 == 0:
                resp += ""
            resp += f"| ![emoticon]({out_path}) | {chr(0xE000 + int(k)):s} | `:{v['aliases']['0']:s}:` "
            if counter % 3 == 2:
                resp += "|\n"

        clear_temp_from_pngs_for_gif()
        if counter % 3 != 2:
            resp += "|\n"
        resp += "\n"

        global_counter += counter + 1

    log.info("❤️❤️❤️ DONE!!! ❤️❤️❤️")
    return resp, global_counter


def build_index(resp: str, emotes_total: int) -> None:
    """
    Build index.md file.

    This page is used in GitHub pages (https://aluerie.github.io/Dota2Utils/ListEmoticons/)
    for an easy way to showcase emoticons.
    """

    today_stats = f"""
<table>
    <tr><td>Last Updated</td><td>{datetime.datetime.now(tz=datetime.UTC).strftime("%d/%B/%Y")}</td></tr>
    <tr><td>Amount of emoticons listed</td><td>{emotes_total}</td></tr>
</table>

"""

    md_file = "./index.md"
    with pathlib.Path(md_file).open("r", encoding="utf-8") as file:
        file_lines = file.readlines()
        old_lines: list[str] = []
        for line in file_lines:
            if not line.startswith("## Table of Dota 2 Emoticons"):
                old_lines.append(line)
            else:
                old_lines.extend(("## Table of Dota 2 Emoticons\n", today_stats))
                break

    with pathlib.Path(md_file).open("w", encoding="utf-8") as file:
        file.writelines(old_lines)

    with pathlib.Path(md_file).open("a", encoding="utf-8") as file:
        file.write(resp)


def main() -> None:
    data = import_vtex_c_files()
    decompile_vtex_c_into_png_series()
    resp, emotes_total = generate_gifs(data)
    build_index(resp, emotes_total)


if __name__ == "__main__":
    main()
