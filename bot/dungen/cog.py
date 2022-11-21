from __future__ import annotations

import logging
import textwrap
from datetime import timedelta

import discord
from discord import Interaction
from discord import app_commands
from discord.ext import commands, tasks

from bot.dungen.schema import DungenAPIRequest
from bot.dungen.services import generate_dungeon, make_map_embed
from bot.dungen.components.views import DungenGenerateView, CaveGeneratedView
from . import choices
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot.bot import DungenBot
log = logging.getLogger(__name__)


class DungeonCog(commands.GroupCog, group_name='dungeon'):
    def __init__(self, bot: DungenBot, expire_views_timedelta: timedelta = timedelta(minutes=1)):
        self.bot = bot
        self.bot.persistent_views
    async def expire_views_task(self):
        pass
    @app_commands.command(name='testing')
    async def testing_cmd(self, itx: Interaction):
        await itx.response.defer(thinking=True)
        await itx.followup.edit_message(itx.message.id, content="bar")

    @app_commands.command(name='map')
    async def map_cmd(self, itx: Interaction):
        view = DungenGenerateView(
                bot=self.bot,
                theme_options=choices.DUNGEN_THEME_OPTIONS,
                size_options=choices.DUNGEON_SIZE_OPTIONS,
                timeout=None
            )
        await itx.response.send_message(
            embed=self.map_embed,
            view=view
        )
        message = await itx.original_response()
        message = await message.fetch()
        view.message = message
        async with self.bot.db as db:
            await view.update_persistent_view(db.connection)


    @app_commands.command(name='cave')
    async def cave_cmd(self, itx: Interaction):
        view = CaveGeneratedView(
                bot=self.bot,
                theme_options=choices.CAVE_THEME_OPTIONS,
                size_options=choices.CAVE_SIZE_OPTIONS,
                default_egress="1",
                timeout=None
        )
        await itx.response.send_message(
            embed=self.map_embed,
            view=view
        )
        message = await itx.original_response()
        message = await message.fetch()
        view.message = message
        async with self.bot.db as db:
            await view.update_persistent_view(db.connection)


    @property
    def map_embed(self):
        desc =  textwrap.dedent("""
        Use the below options to generate your own Dungeon. All seeds are random by default.
        """)
        embed = discord.Embed(title="Generate New Embed", description=desc)
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
