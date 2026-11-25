"""Read files from Dota 2's `pak01` VPK: from the local Dota 2 install, or straight from Steam's content servers.

Reading from Steam needs a logged-in account that has Dota 2 in its library (anonymous accounts get no depot keys).
The archives are tens of gigabytes, so `SteamVPK` downloads only the small VPK index and then the byte ranges
of the requested files.
"""

from __future__ import annotations

import asyncio
import contextlib
import zlib
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Protocol
lazy from collections.abc import AsyncGenerator

import steam
import vpk

from dota2utils_common import Dota2UtilsError, steam as local_steam
from dota2utils_common.logs import logger

if TYPE_CHECKING:
    import pathlib
    from collections.abc import Iterable

__all__ = (
    "LocalVPK",
    "SteamVPK",
    "VPKFiles",
    "steam_login",
)

DOTA_APP_ID = 570
PAK_FOLDER = "game/dota"
PAK_DIR_FILE = "pak01_dir.vpk"
# `archive_index` of files stored inside the `_dir.vpk` itself;
EMBEDDED_ARCHIVE = 0x7FFF
# Files in the same archive closer than this are read in one request - Steam serves files in chunks of up to 1 MiB,
# so a smaller gap would download the same chunks twice;
MERGE_GAP = 1 << 20
PARALLEL_READS = 8


class VPKFiles(Protocol):
    async def read_many(self, paths: Iterable[str]) -> dict[str, bytes]:
        """Contents of the files at `paths` (paths inside the VPK); files that don't exist are left out."""
        ...


class LocalVPK:
    """The VPK of the locally installed Dota 2."""

    def __init__(self, dir_file: pathlib.Path) -> None:
        self.pak = vpk.open(str(dir_file))

    @classmethod
    def from_dota_install(cls) -> LocalVPK:
        return cls(local_steam.dota_path() / PAK_FOLDER / PAK_DIR_FILE)

    async def read_many(self, paths: Iterable[str]) -> dict[str, bytes]:
        files: dict[str, bytes] = {}
        for path in paths:
            with contextlib.suppress(KeyError):
                files[path] = self.pak[path].read()
        return files


class SteamVPK:
    """The VPK of the current Dota 2 build on Steam, read without downloading the game."""

    def __init__(self, index: vpk.VPK, archives: dict[int, steam.ManifestPath]) -> None:
        self.index = index
        self.archives = archives

    @classmethod
    async def fetch(cls, client: steam.Client, cache_dir: pathlib.Path) -> SteamVPK:
        """Find the `pak01` files in Dota 2's depots and download the VPK index into `cache_dir`."""
        files = await _find_pak01_files(client)
        dir_file = files.pop(PAK_DIR_FILE, None)
        if dir_file is None:
            msg = f"`{PAK_FOLDER}/{PAK_DIR_FILE}` not found in any Dota 2 depot this Steam account can access."
            raise Dota2UtilsError(msg)

        logger.info("📥 Downloading the VPK index ({:.0f} MB)", dir_file.size / 1e6)
        async with dir_file.open() as file:
            data = await file.read()
        index_path = cache_dir / PAK_DIR_FILE
        await asyncio.to_thread(_write_file, index_path, data)

        # `pak01_123.vpk` -> 123;
        archives = {
            int(number): path
            for name, path in files.items()
            if (number := name.removeprefix("pak01_").removesuffix(".vpk")).isdigit()
        }
        return cls(vpk.open(str(index_path)), archives)

    async def read_many(self, paths: Iterable[str]) -> dict[str, bytes]:
        metas: dict[str, dict[str, Any]] = {}
        for path in paths:
            with contextlib.suppress(KeyError):
                metas[path] = self.index.get_file_meta(path)

        files: dict[str, bytes] = {}
        by_archive: defaultdict[int, list[str]] = defaultdict(list)
        for path, meta in metas.items():
            if meta["archive_index"] == EMBEDDED_ARCHIVE:
                files[path] = self.index[path].read()  # the index file is local - nothing to download;
            elif meta["file_length"] == 0:
                files[path] = meta["preload"]  # all of it is in the index;
            else:
                by_archive[meta["archive_index"]].append(path)

        groups = [group for group_paths in by_archive.values() for group in merge_nearby(group_paths, metas)]
        semaphore = asyncio.Semaphore(PARALLEL_READS)

        async def read_group(group: list[str]) -> None:
            archive = metas[group[0]]["archive_index"]
            if archive not in self.archives:
                msg = f"VPK archive pak01_{archive:03d}.vpk is missing from the Steam depots."
                raise Dota2UtilsError(msg)
            start = metas[group[0]]["archive_offset"]
            end = max(metas[path]["archive_offset"] + metas[path]["file_length"] for path in group)
            async with semaphore:
                blob = await self.archives[archive].read_range(start, end - start)
            for path in group:
                meta = metas[path]
                offset = meta["archive_offset"] - start
                data = meta["preload"] + blob[offset : offset + meta["file_length"]]
                if zlib.crc32(data) != meta["crc32"]:
                    msg = f"Checksum mismatch for {path} downloaded from Steam."
                    raise Dota2UtilsError(msg)
                files[path] = data

        logger.info("📥 Downloading {} files in {} requests", sum(len(group) for group in groups), len(groups))
        await asyncio.gather(*(read_group(group) for group in groups))
        return files


def _write_file(path: pathlib.Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def merge_nearby(paths: list[str], metas: dict[str, dict[str, Any]]) -> list[list[str]]:
    """Group files of one archive that lie within `MERGE_GAP` of each other, ordered by offset."""
    groups: list[list[str]] = []
    group_end = -MERGE_GAP - 1
    for path in sorted(paths, key=lambda path: metas[path]["archive_offset"]):
        start = metas[path]["archive_offset"]
        if start - group_end <= MERGE_GAP:
            groups[-1].append(path)
        else:
            groups.append([path])
        group_end = max(group_end, start + metas[path]["file_length"])
    return groups


async def _find_pak01_files(client: steam.Client) -> dict[str, steam.ManifestPath]:
    """`pak01_*.vpk` file name (lowercase) -> file, across the Dota 2 depots this account can access."""
    (info,) = await client.fetch_product_info(apps=[steam.App(id=DOTA_APP_ID)])
    files: dict[str, steam.ManifestPath] = {}
    for manifest_info in info.public_branch.manifests:
        try:
            manifest = await manifest_info.fetch()
        except steam.SteamException as exc:
            # Depots of other platforms/languages can be off-limits; the ones we need are not;
            logger.debug("Skipping depot {}: {}", manifest_info.depot.id, exc)
            continue
        for path in manifest.paths:
            folder, _, name = str(path).replace("\\", "/").strip("/").rpartition("/")
            if folder.lower() == PAK_FOLDER and name.lower().startswith("pak01_"):
                files[name.lower()] = path
    return files


@contextlib.asynccontextmanager
async def steam_login(**credentials: str) -> AsyncGenerator[steam.Client]:
    """A logged-in Steam client for the duration of the `async with` block.

    `credentials` are passed to `steam.Client.login`, e.g. `username=..., password=...`
    (steam.py asks for a Steam Guard code in the terminal if the account needs one).
    """
    client = steam.Client()
    async with client:
        login = asyncio.create_task(client.login(**credentials))
        ready = asyncio.create_task(client.wait_until_ready())
        await asyncio.wait({login, ready}, return_when=asyncio.FIRST_COMPLETED)
        if not ready.done():
            ready.cancel()
            await login  # re-raises the login error;
            msg = "Steam login ended before the client was ready."
            raise Dota2UtilsError(msg)
        try:
            yield client
        finally:
            await client.close()
            await login
