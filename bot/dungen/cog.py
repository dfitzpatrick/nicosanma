from __future__ import annotations

import logging
import textwrap
from datetime import timedelta
from typing import TYPE_CHECKING, Optional

import discord
from discord import Interaction
from discord import app_commands
from discord.ext import commands

from bot.dungen.components.views import DungenGenerateView, CaveGeneratedView
from bot.dungen.schema import DungenAPIRequest
from bot.dungen.services import generate_dungeon, make_map_embed, PATREON_URL
from . import choices

if TYPE_CHECKING:
    from bot.bot import DungenBot
log = logging.getLogger(__name__)


class DungeonCog(commands.GroupCog, group_name='dungen'):
    def __init__(self, bot: DungenBot, expire_views_timedelta: timedelta = timedelta(minutes=1)):
        self.bot = bot

    @app_commands.command(name='map', description="Starts a new Map Generator session with DunGen")
    async def map_cmd(self, itx: Interaction):
        view = DungenGenerateView(
                bot=self.bot,
                theme_options=choices.DUNGEN_THEME_OPTIONS,
                size_options=choices.DUNGEON_SIZE_OPTIONS,
                timeout=None
            )
        await itx.response.send_message(
            embed=self.map_embed(title="New Map Generator"),
            view=view
        )
        message = await itx.original_response()
        message = await message.fetch()
        view.message = message
        async with self.bot.db as db:
            await view.update_persistent_view(db.connection)

    @app_commands.command(name='cave', description="Starts a new Cave Generator session with DunGen")
    async def cave_cmd(self, itx: Interaction):
        view = CaveGeneratedView(
                bot=self.bot,
                theme_options=choices.CAVE_THEME_OPTIONS,
                size_options=choices.CAVE_SIZE_OPTIONS,
                default_egress="1",
                timeout=None
        )
        await itx.response.send_message(
            embed=self.map_embed(title="New Cave Generator"),
            view=view
        )
        message = await itx.original_response()
        message = await message.fetch()
        view.message = message
        async with self.bot.db as db:
            await view.update_persistent_view(db.connection)

    def map_embed(self, title: Optional[str] = None, description: Optional[str] = None):
        desc = description or textwrap.dedent(f"""
        Use the below options and then click Generate. All seeds are random by default.
        Make sure to check out our [patreon]({PATREON_URL}) for some awesome perks.
        """)
        title = title or "New Generator"
        embed = discord.Embed(title=title, description=desc)
        embed.set_author(
            name="Dungeon Channel", url=PATREON_URL,
            icon_url="https://dungeonchannel.com/mainimages/patreon/Patreon_Coral.jpg"
        )
        return embed

    async def _handle_create_cmd(self, itx: Interaction, size: int, theme: str, tile_size: int):
        await itx.response.defer(thinking=True)
        req = DungenAPIRequest(
            seed="random",
            theme=theme,
            max_size=size,
            tile_size=tile_size
        )
        dungen_response = await generate_dungeon(req)
        embed = make_map_embed(dungen_response)
        await itx.followup.send(embed=embed)


async def setup(bot: DungenBot):
    await bot.add_cog(DungeonCog(bot))
