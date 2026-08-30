from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

import aiohttp
import orjson

if TYPE_CHECKING:
    from steam.ext.dota2 import Hero
    from typings import api_schemas

log = logging.getLogger()
log.setLevel(logging.INFO)


class D2PTClient:
    async def invoke(self, endpoint: str) -> Any:
        url = f"https://dota2protracker.com{endpoint}"
        log.info("D2PTClient: Sending a request to %s", url)

        async def attempt() -> Any:
            async with (
                aiohttp.ClientSession() as session,
                session.get(
                    url=f"https://dota2protracker.com{endpoint}",
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/104.0.0.0 Safari/537.36"
                        ),
                        "Accept": "application/json, text/plain, */*",
                        "Accept-Language": "en-US,en;q=0.9",
                    },
                ) as resp,
            ):
                res = await resp.json(loads=orjson.loads)

                if res == {"message": "Forbidden"}:
                    msg = '{"message": "Forbidden"}'
                    raise RuntimeError(msg)
                return res

        counter = 0
        while counter < 10:
            counter += 1
            log.info("attempt #%s", counter)
            try:
                return await attempt()
            except RuntimeError:
                await asyncio.sleep(counter * 2**counter)
                continue
        msg = "Failed too many times"
        raise RuntimeError(msg)

    async def item_overview(self, hero: Hero, position: int) -> api_schemas.ItemOverview:
        """

        Example:
        * https://dota2protracker.com/hero/Dark%20Willow/api/item-overview?heroId=119&position=pos+4&period=full
        """
        return await self.invoke(
            f"/hero/{hero.display_name}/api/item-overview?heroId={hero.id}&position=pos+{position}&period=full",
        )

    async def patches(self) -> api_schemas.Patches:
        """

        Example:
        * https://dota2protracker.com/api/patches
        """
        return await self.invoke("/api/patches")

    async def hero_matches(self, hero: Hero, position: int) -> api_schemas.Matches:
        """

        Example:
        * https://dota2protracker.com/api/hero-matches?hero_id=119&position=pos+4&sort_by=mmr
        """
        return await self.invoke(f"/api/hero-matches?hero_id={hero.id}&position=pos+{position}&sort_by=mmr")


class OpenDotaClient:
    """A class for interacting with OpenDota API."""

    async def invoke(self, endpoint: str) -> Any:
        """Invoke a request to OpenDota API."""
        async with aiohttp.ClientSession() as session, session.get(url=f"https://api.opendota.com/api/{endpoint}") as resp:
            return await resp.json(loads=orjson.loads)

    async def get_items(self) -> api_schemas.OpendotaItemsQuery:
        """Get Opendota constants items.

        Links
        -----
        * https://api.opendota.com/api/constants/items
        * https://raw.githubusercontent.com/odota/dotaconstants/master/build/items.json
        """
        log.debug("🍋 Opendota Constants API: getting items.")
        return await self.invoke("constants/items")
