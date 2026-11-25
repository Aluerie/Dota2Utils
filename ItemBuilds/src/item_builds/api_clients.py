from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import aiohttp
import orjson

from dota2utils_common.logs import logger

if TYPE_CHECKING:
    from steam.ext.dota2 import Hero

    from . import api_schemas

__all__ = (
    "REQUEST_ERRORS",
    "D2PTClient",
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}
MAX_ATTEMPTS = 10
# D2PT often refuses the hero-matches endpoint for a long time; it's only needed for a few early items
# and Stratz can stand in for it, so don't wait long;
HERO_MATCHES_ATTEMPTS = 2
# What a failed request raises: HTTP errors (403/429/5xx), HTML instead of JSON, network errors and timeouts;
REQUEST_ERRORS = (RuntimeError, aiohttp.ClientError, TimeoutError)


def retry_delay(attempt: int) -> int:
    """Seconds to wait after failed attempt number `attempt`: 30s, 60s, 120s, ... capped at 15 minutes."""
    return min(30 * 2 ** (attempt - 1), 900)


class D2PTClient:
    """Client for the (semi-public) JSON API behind dota2protracker.com pages.

    D2PT rate-limits aggressively, so every request is retried with a growing delay (~1 hour in total at worst).
    """

    @staticmethod
    async def _request(url: str) -> Any:
        async with (
            aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session,
            session.get(url=url, headers=HEADERS) as resp,
        ):
            # Raises `aiohttp.ClientResponseError` on 4xx/5xx (i.e. 429 rate limits);
            resp.raise_for_status()
            # Raises `aiohttp.ContentTypeError` if we got served an HTML page (i.e. Cloudflare);
            res = await resp.json(loads=orjson.loads)
            if res == {"message": "Forbidden"}:
                msg = '{"message": "Forbidden"}'
                raise RuntimeError(msg)
            return res

    async def invoke(self, endpoint: str, max_attempts: int = MAX_ATTEMPTS) -> Any:
        url = f"https://dota2protracker.com{endpoint}"
        logger.info("🌐 D2PT: requesting {}", url)

        for attempt in range(1, max_attempts):
            try:
                return await self._request(url)
            except REQUEST_ERRORS as exc:
                delay = retry_delay(attempt)
                # `str()` of aiohttp errors is short ("403, message='Forbidden', url=..."), `repr()` dumps all headers;
                logger.warning(
                    "⏳ D2PT: attempt #{} failed ({}: {}), retrying in {}s", attempt, type(exc).__name__, exc, delay
                )
                await asyncio.sleep(delay)

        # Last attempt - let the error propagate;
        return await self._request(url)

    async def item_overview(self, hero: Hero, position: int) -> api_schemas.ItemOverview:
        """Item overview for a hero in a position. It seems the data is from high+elite MMR.

        Mirrors pages like https://dota2protracker.com/hero/Dark%20Willow?section=items

        Example: https://dota2protracker.com/hero/Dark%20Willow/api/item-overview?heroId=119&position=pos+4&period=full
        """
        return await self.invoke(
            f"/hero/{hero.display_name}/api/item-overview?heroId={hero.id}&position=pos+{position}&period=full",
        )

    async def patches(self) -> api_schemas.Patches:
        """Dota 2 patches, newest first.

        Example: https://dota2protracker.com/api/patches
        """
        return await self.invoke("/api/patches")

    async def hero_matches(self, hero: Hero, position: int) -> api_schemas.Matches:
        """Hero matches in a position for the last ~2 months. It seems these matches are elite MMR only.

        Mirrors pages like https://dota2protracker.com/hero/Dark%20Willow?section=matches&role=support

        Example: https://dota2protracker.com/api/hero-matches?hero_id=119&position=pos+4&sort_by=mmr
        """
        return await self.invoke(
            f"/api/hero-matches?hero_id={hero.id}&position=pos+{position}&sort_by=mmr",
            max_attempts=HERO_MATCHES_ATTEMPTS,
        )
