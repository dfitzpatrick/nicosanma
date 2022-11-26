from __future__ import annotations

import json
import logging
import random
import re
from datetime import timedelta
from typing import Optional, Dict, Any

import aiohttp
import asyncpg
import discord
from pydantic import BaseModel

from bot.dungen.schema import DungenAPIRequest, DungenAPIResponse, CaveAPIRequest, CaveAPIResponse, GeneratedAPIResponse
from . import config_constants

log = logging.getLogger(__name__)

PATREON_URL = "https://www.patreon.com/DungeonChannel"


async def generate(req: BaseModel, target_url: str, exclude_seed: bool = False) -> Dict[str, Any]:
    excludes = {'seed'} if exclude_seed else set()
    payload = req.json(exclude=excludes)
    headers = {"Content-Type": "application/json"}
    log.debug(f"Calling Post to {target_url} headers={headers}")
    log.debug(f"Payload: {req}")
    async with aiohttp.ClientSession(raise_for_status=True) as session:
        async with session.post(target_url, data=payload, headers=headers) as response:
            response = await response.json()
            log.debug(f"Response: {response}")
            return response


async def generate_dungeon(req: DungenAPIRequest) -> DungenAPIResponse:
    target = "https://dungen.app/api/generate/"
    response = await generate(req, target)
    return DungenAPIResponse(**response)


async def generate_cave(req: CaveAPIRequest, exclude_seed: bool = False) -> CaveAPIResponse:
    target = "https://dungen.app/api/cave/"
    response = await generate(req, target, exclude_seed=exclude_seed)
    return CaveAPIResponse(**response)


def make_response_embed(title: str, dungen_response: GeneratedAPIResponse, **kwargs):
    patreon_choice = random.choices([
        f"Your options have been generated!",
        f"If you're enjoying the bot, make sure to take a look at our [patreon]({PATREON_URL}) for some awesome perks.",
        "If you need to report a problem or would like to leave some feedback (very much appreciated!), please join the official [DunGen Discord](https://discord.gg/sBu5W4D)",
        "New features are first tested in the official discord server. If you'd like to test them out before they're publicly released, you can join us [here](https://discord.gg/sBu5W4D)",
        "You can also use DunGen directly on our website: [DunGen.app](https://dungen.app/dungen/)",
        "**v0.8 Update** - DunGen now supports Automatic Dynamic Lighting for Roll20. Check our website [DunGen.app](https://dungen.app/faq/) for more information."
    ], [5, 2, 1, 1, 15, 5])[0]
    log.debug(dungen_response.full_image_url)
    embed = discord.Embed(title=title, description=patreon_choice)
    embed.set_author(name=config_constants.SERVICE_NAME, url=config_constants.PATREON_URL,
                     icon_url=config_constants.SERVICE_ICON)
    embed.set_image(url=dungen_response.full_image_url)
    embed.add_field(name="Map Size", value=dungen_response.max_tile_size_fmt, inline=True)
    embed.add_field(name="File Size", value=dungen_response.file_size_fmt, inline=True)
    embed.add_field(name="Seed", value=dungen_response.seed_string, inline=True)
    return embed


def make_map_embed(dungen_response: DungenAPIResponse, **kwargs) -> discord.Embed:
    embed = make_response_embed(title="Map Generated!", dungen_response=dungen_response)
    return embed


def make_cave_embed(dungen_response: CaveAPIResponse, **kwargs) -> discord.Embed:
    embed = make_response_embed(title="Cave Generated!", dungen_response=dungen_response)
    return embed


def patreon_embed(*, title=None, description=None, **kwargs):
    default_title = "Uh Oh, You must be a Patreon Member to access this!"
    default_description = f"Get access to all the best features by becoming a [Patreon Member]({PATREON_URL}) today."
    embed = discord.Embed(title=title or default_title, description=description or default_description, **kwargs)
    return embed


async def update_persistant_view(conn: asyncpg.Connection, designation: str, message: discord.Message, view_state: Dict[str, Any]):
    payload = json.dumps(view_state)
    if message.guild is None:
        log.debug("Message is a Partial Message. Running Update Only on persistent view")
        # A partial message means that likely this view already has a record in the database. Update the payload
        sql = """
        update discord_persistent_views
        set view_payload = $1
        where message_id = $2
        """
        await conn.execute(sql, payload, message.id)
    else:
        log.debug("Found full message details. Doing upsert on persistent view")
        sql = """
        insert into discord_persistent_views (designation, guild_id, channel_id, message_id, view_payload)
        values ($1, $2, $3, $4, $5)
        on conflict (message_id)
        do
            update set view_payload = $5
        """
        await conn.execute(sql, designation, message.guild.id, message.channel.id, message.id, payload)


def text_timedelta(text: str) -> Optional[timedelta]:
    """Takes a text representation of time like url timestamps and converts it to a timedelta
    Format is 1w2d1h18m2s
    """
    pattern = '^(?:(?P<weeks>\d+)[w.])?(?:(?P<days>\d+)[d.])?(?:(?P<hours>\d+)[h.])?(?:(?P<minutes>\d+)[m.])?(?:(?P<seconds>\d+)[s.])?$'
    pattern = re.compile(pattern)
    matches = re.search(pattern, text)
    if matches is None:
        log.error(f"Invalid string {text}")
        return
    args = {k: int(v) for k, v in matches.groupdict().items() if v and v.isdigit()}
    return timedelta(**args)


