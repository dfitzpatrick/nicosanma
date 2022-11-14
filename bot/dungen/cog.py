from __future__ import annotations

import logging
import textwrap

import discord
from discord import Interaction
from discord import app_commands
from discord.ext import commands

from bot.dungen.schema import DungenAPIRequest
from bot.dungen.services import generate_dungeon, make_dungeon_embed
from bot.dungen.views import DungenGenerateView, CaveGeneratedView
from . import choices

log = logging.getLogger(__name__)


class DungeonCog(commands.GroupCog, group_name='dungeon'):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name='map')
    async def map_cmd(self, itx: Interaction):
        await itx.response.send_message(
            embed=self.map_embed,
            view=DungenGenerateView(
                theme_options=choices.DUNGEN_THEME_OPTIONS,
                size_options=choices.DUNGEON_SIZE_OPTIONS,
            )
        )

    @app_commands.command(name='cave')
    async def cave_cmd(self, itx: Interaction):
        await itx.response.send_message(
            embed=self.map_embed,
            view=CaveGeneratedView(
                theme_options=choices.CAVE_THEME_OPTIONS,
                size_options=choices.CAVE_SIZE_OPTIONS,
                default_egress="1"
            )
        )

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
        embed = make_dungeon_embed(dungen_response)
        await itx.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(DungeonCog(bot))
