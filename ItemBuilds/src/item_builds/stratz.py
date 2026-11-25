"""Item purchase stats from the Stratz GraphQL API (https://stratz.com/api), used when D2PT refuses match data."""

from __future__ import annotations

from collections import Counter
from typing import Any

import aiohttp
import orjson

from dota2utils_common.logs import logger

__all__ = (
    "StratzClient",
    "purchase_shares",
)

URL = "https://api.stratz.com/graphql"
# High-MMR first (like D2PT's data); heroes with few games there get no item rows, so fall back to all brackets;
# (`None` = no bracket filter - Stratz returns nothing for the `ALL` bracket value)
BRACKETS: tuple[list[str] | None, ...] = (["DIVINE_IMMORTAL"], None)
QUERY = """
query ($hero: Short!, $positions: [MatchPlayerPositionType], $brackets: [RankBracketBasicEnum]) {
  heroStats {
    stats(heroIds: [$hero], positionIds: $positions, bracketBasicIds: $brackets) { matchCount }
    itemFullPurchase(heroId: $hero, positionIds: $positions, bracketBasicIds: $brackets) { itemId matchCount }
  }
}
"""


def purchase_shares(data: dict[str, Any]) -> dict[int, float]:
    """Item ID -> share of the hero's matches it was bought in, from a `QUERY` response (empty if no data).

    Stratz counts purchases (split by game minute), not matches, so shares are a bit inflated
    and capped at 100% - good enough to tell "most players buy it" from "almost nobody does".
    """
    hero_stats = data.get("heroStats") or {}
    total = sum(row["matchCount"] or 0 for row in hero_stats.get("stats") or [])
    rows = hero_stats.get("itemFullPurchase") or []
    if not total or not rows:
        return {}
    purchases: Counter[int] = Counter()
    for row in rows:
        purchases[row["itemId"]] += row["matchCount"] or 0
    return {item_id: min(count / total, 1.0) for item_id, count in purchases.items()}


class StratzClient:
    """Minimal Stratz GraphQL client. Needs a (free) API token."""

    def __init__(self, token: str) -> None:
        self.token = token

    async def _query(self, variables: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.token}",
            # Stratz asks API clients to identify themselves with this User-Agent;
            "User-Agent": "STRATZ_API",
            "Content-Type": "application/json",
        }
        async with (
            aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session,
            session.post(URL, json={"query": QUERY, "variables": variables}, headers=headers) as resp,
        ):
            resp.raise_for_status()
            result = await resp.json(loads=orjson.loads)
        if errors := result.get("errors"):
            msg = f"Stratz: {errors[0].get('message', errors)}"
            raise RuntimeError(msg)
        return result["data"]

    async def item_purchase_shares(self, hero_id: int, position: int) -> dict[int, float]:
        """Item ID -> share of matches it's bought in, for the hero in a position (1-5); empty if Stratz has no data."""
        for brackets in BRACKETS:
            logger.info("🌐 Stratz: item purchases for hero {} pos {} ({})", hero_id, position, brackets or "all brackets")
            data = await self._query({"hero": hero_id, "positions": [f"POSITION_{position}"], "brackets": brackets})
            if shares := purchase_shares(data):
                return shares
        return {}
