from __future__ import annotations

from typing import List, Optional

import aiohttp
import discord
import random
from bot.dungen.schema import DungenAPIRequest, DungenAPIResponse
import logging

log = logging.getLogger(__name__)

async def generate_dungeon(req: DungenAPIRequest) -> DungenAPIResponse:
    target = "https://dungen.app/api/generate/"
    payload = req.json()
    log.debug(payload)
    headers = {"Content-Type": "application/json"}
    async with aiohttp.ClientSession(raise_for_status=True) as session:
        async with session.post(target, data=payload, headers=headers) as response:
            response = await response.json()
            return DungenAPIResponse(**response)


def make_dungeon_embed(dungen_response: DungenAPIResponse, **kwargs) -> discord.Embed:
    patreon_url = "https://www.patreon.com/DungeonChannel"
    member = kwargs.get('member')
    member_mention = member.mention if member is not None else "!"
    patreon_choice = random.choices([
        f"Your dungeon has been generated {member_mention}",
        f"If you're enjoying the bot, make sure to take a look at our [patreon]({patreon_url}) for some awesome perks.",
        "If you need to report a problem or would like to leave some feedback (very much appreciated!), please join the official [DunGen Discord](https://discord.gg/sBu5W4D)",
        "New features are first tested in the official discord server. If you'd like to test them out before they're publicly released, you can join us [here](https://discord.gg/sBu5W4D)",
        "You can also use DunGen directly on our website: [DunGen.app](https://dungen.app/dungen/)",
        "**v0.8 Update** - DunGen now supports Automatic Dynamic Lighting for Roll20. Check our website [DunGen.app](https://dungen.app/faq/) for more information."
    ], [5, 2, 1, 1, 15, 5])[0]

    embed = discord.Embed(title="DunGen Completed!", description=patreon_choice)
    embed.set_author(name="Dungeon Channel", url=patreon_url, icon_url="https://dungeonchannel.com/mainimages/patreon/Patreon_Coral.jpg")
    embed.set_image(url=dungen_response.full_image_url)
    embed.add_field(name="Map Size", value=dungen_response.max_tile_size_fmt, inline=True)
    embed.add_field(name="File Size", value=dungen_response.file_size_fmt, inline=True)
    embed.add_field(name="Seed", value=dungen_response.seed_string, inline=True)
    embed.add_field(name="Download", value=f"[Click here]({dungen_response.full_image_url})", inline=True)

    return embed

def find_select_option_index_by_value(self, options: List[discord.SelectOption], value: str) -> Optional[int]:
    for idx, so in enumerate(options):
        if so.value == value:
            return idx