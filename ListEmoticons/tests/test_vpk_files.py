from __future__ import annotations

import asyncio
import zlib
from typing import Any

import pytest

from dota2utils_common import Dota2UtilsError
from list_emoticons import vpk_files
from list_emoticons.vpk_files import MERGE_GAP, SteamVPK

ARCHIVE = bytes(range(256)) * 16_384  # 4 MiB of recognizable bytes


class FakeArchive:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.reads: list[tuple[int, int]] = []

    async def read_range(self, offset: int, size: int) -> bytes:
        self.reads.append((offset, size))
        return self.data[offset : offset + size]


class FakeIndex:
    def __init__(self, metas: dict[str, dict[str, Any]]) -> None:
        self.metas = metas

    def get_file_meta(self, path: str) -> dict[str, Any]:
        return self.metas[path]

    def __getitem__(self, path: str) -> Any:
        msg = "embedded files are not used in these tests"
        raise AssertionError(msg)


def meta(offset: int, length: int, *, archive: int = 1, preload: bytes = b"", crc: int | None = None) -> dict[str, Any]:
    data = preload + ARCHIVE[offset : offset + length]
    return {
        "preload": preload,
        "crc32": zlib.crc32(data) if crc is None else crc,
        "preload_length": len(preload),
        "archive_index": archive,
        "archive_offset": offset,
        "file_length": length,
    }


def steam_vpk(metas: dict[str, dict[str, Any]]) -> tuple[SteamVPK, dict[int, FakeArchive]]:
    archives = {1: FakeArchive(ARCHIVE), 2: FakeArchive(ARCHIVE)}
    index: Any = FakeIndex(metas)  # duck-typed fakes of `vpk.VPK` and `steam.ManifestPath`;
    fake_archives: Any = archives
    return SteamVPK(index, fake_archives), archives


def test_read_many_merges_nearby_files() -> None:
    metas = {
        "a": meta(100, 50),
        "b": meta(200, 30),  # close to "a" - same request
        "c": meta(100 + 3 * MERGE_GAP, 10),  # far away - its own request
        "d": meta(500, 20, archive=2),  # other archive
        "e": meta(0, 0, preload=b"tiny"),  # all in the index - nothing to download
    }
    files, archives = steam_vpk(metas)

    result = asyncio.run(files.read_many([*metas, "missing"]))

    assert result == {
        "a": ARCHIVE[100:150],
        "b": ARCHIVE[200:230],
        "c": ARCHIVE[100 + 3 * MERGE_GAP : 110 + 3 * MERGE_GAP],
        "d": ARCHIVE[500:520],
        "e": b"tiny",
    }
    assert sorted(archives[1].reads) == [(100, 130), (100 + 3 * MERGE_GAP, 10)]
    assert archives[2].reads == [(500, 20)]


def test_read_many_prepends_preload() -> None:
    files, _ = steam_vpk({"a": meta(1000, 10, preload=b"head")})
    assert asyncio.run(files.read_many(["a"])) == {"a": b"head" + ARCHIVE[1000:1010]}


def test_read_many_checks_crc() -> None:
    files, _ = steam_vpk({"a": meta(0, 10, crc=12345)})
    with pytest.raises(Dota2UtilsError, match="Checksum mismatch"):
        asyncio.run(files.read_many(["a"]))


def test_read_many_missing_archive() -> None:
    files, _ = steam_vpk({"a": meta(0, 10, archive=7)})
    with pytest.raises(Dota2UtilsError, match=r"pak01_007\.vpk"):
        asyncio.run(files.read_many(["a"]))


def test_merge_nearby_handles_overlaps() -> None:
    metas = {"big": meta(0, 5000), "inside": meta(100, 10), "after": meta(5000 + MERGE_GAP + 1, 10)}
    assert vpk_files.merge_nearby(list(metas), metas) == [["big", "inside"], ["after"]]
