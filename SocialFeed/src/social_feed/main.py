"""Post messages into your Dota 2 profile's User Feed widget.

Valve removed the UI for this, but the Game Coordinator messages still work.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from steam.ext.dota2 import Client

from dota2utils_common import ConfigError, config
from dota2utils_common.logs import logger, setup_logging

if TYPE_CHECKING:
    from collections.abc import Sequence

LYRICS = """I want to hold the hand inside you
I want to take the breath that's true
I look to you, and I see nothing
I look to you to see the truth
You live your life, you go in shadows
You'll come apart, and you'll go black
Some kind of night into your darkness
Colors your eyes with what's not there
Fade into you
Strange you never knew
Fade into you
I think it's strange you never knew
A stranger light comes on slowly
A stranger's heart without a home
You put your hands into your head
And then its smiles cover your heart
Fade into you
Strange you never knew
Fade into you
I think it's strange you never knew
Fade into you
Strange you never knew
Fade into you
I think it's strange you never knew
I think it's strange you never knew"""

# The feed shows the newest message on top, so post the lines bottom-up;
MESSAGES_TO_POST = LYRICS.splitlines()[::-1]
# There seems to be a rate limit;
SLEEP_BETWEEN_MESSAGES = 10.0


class FeedPoster(Client):
    """Dota 2 client that posts `feed_messages` to the User Feed once it's ready, then disconnects."""

    def __init__(self, feed_messages: Sequence[str]) -> None:
        super().__init__()
        # Not `self.messages` - that's a read-only property of `steam.Client` (chat messages);
        self.feed_messages = feed_messages
        self.posted = False

    async def on_ready(self) -> None:
        # `on_ready` can fire again after a reconnect - don't post everything twice.
        if self.posted:
            return
        self.posted = True

        for message in self.feed_messages:
            await self.user.post_social_message(message=message)
            logger.info("💬 Sent '{}' to the User Feed widget.", message)
            await asyncio.sleep(SLEEP_BETWEEN_MESSAGES)

        logger.success("😘😘😘 Done! Closing the client.")
        await self.close()


async def post_messages() -> None:
    username = config.require("steam", "username")
    password = config.require("steam", "password")
    client = FeedPoster(MESSAGES_TO_POST)
    async with client:
        # `login` prompts for a Steam Guard code itself if needed and returns once the client is closed.
        await client.login(username=username, password=password)


def main() -> None:
    """Log into Steam and post the messages."""
    setup_logging()
    try:
        asyncio.run(post_messages())
    except ConfigError as exc:
        logger.error(str(exc))
        raise SystemExit(1) from exc
