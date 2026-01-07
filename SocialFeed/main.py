from __future__ import annotations

import asyncio
import logging

from steam.ext.dota2 import Client

from config import STEAM_PASSWORD, STEAM_USERNAME

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

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
I think it's strange you never knew"""

MESSAGES_TO_POST = LYRICS.splitlines()[::-1]

dota = Client()


@dota.event
async def on_ready() -> None:
    for message in MESSAGES_TO_POST:
        await dota.user.post_social_message(message=message)
        log.info("Sent %s to the User Feed Widget.", message)

        # It seems there is some rate-limit
        await asyncio.sleep(10.0)

    log.info("Done! 😘😘😘 You can close the script.")


async def main() -> None:
    async with dota:
        await dota.login(username=STEAM_USERNAME, password=STEAM_PASSWORD)
        await dota.code()

        # OR
        # await dota.login(refresh_token=REFRESH_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
