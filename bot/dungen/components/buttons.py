from __future__ import annotations

import uuid

import discord
from discord import ui
from typing import TYPE_CHECKING, Type, Callable

from bot.dungen.schema import CaveAPIRequest
from bot.dungen.services import patreon_embed
from .modals import CallbackModal
import logging

from .. import config_constants

if TYPE_CHECKING:
    from .views import DungenGenerateView, GeneratedMapView, CaveGeneratedView

log = logging.getLogger(__name__)

class GenerateButton(ui.Button):

    def __init__(self, **kwargs):
        super(GenerateButton, self).__init__(**kwargs)

    async def callback(self, itx: discord.Interaction):
        """
        Duplicated defer() on each branch to prevent the bot from getting stuck in thining
        Apparently edit_message does not signal thinking to stop.

        Thinking, however, is needed to grab the correct message to attach to the view.
        The else branch spawns a new view with a new custom id to track in the database.
        Parameters
        """
        view: GeneratedMapView = self.view
        if view.regenerated:
            await itx.response.defer()
            embed = await view.generate()
            await itx.followup.edit_message(itx.message.id, embed=embed, view=view.as_new_view())
        else:
            await itx.response.defer(thinking=True)
            embed = await view.generate()
            view = view.as_new_view(custom_id_prefix=str(uuid.uuid4()))

            await itx.followup.send(embed=embed, view=view)
            message = await itx.original_response()
            view.message = message
        async with view.bot.db as db:
            await view.update_persistent_view(db.connection)


class UpscaleButton(ui.Button):

    def __init__(self, always_allow: bool = False, **kwargs):
        super(UpscaleButton, self).__init__(**kwargs)
        self.always_allow = always_allow

    async def callback(self, itx: discord.Interaction):
        view: GeneratedMapView = self.view
        discord_id = str(itx.user.id)
        await itx.response.defer()
        sql = """
        select count(t.patreon_id) from patreon_tiers t
        left join patreon_social_connections c on c.patreon_id = t.patreon_id
        left join patreons p on t.patreon_id = p.patreon_id
        where p.active = true
        and t.tier_id in (3313110, 7161052)
        and c.provider_name = 'discord'
        and c.provider_id = $1
         """
        count = 0
        if not self.always_allow:
            async with view.bot.db as db:
                count = await db.connection.fetchval(sql, discord_id)
        if self.always_allow or count > 0:
            view.tile_size = 140
            embed = await view.generate()
            if view.message:
                async with view.bot.db as db:
                    await view.update_persistent_view(db.connection)
            if view.regenerated:
                await itx.followup.edit_message(itx.message.id, embed=embed, view=view.as_new_view())
            else:
                await itx.followup.send(embed=embed, view=view.as_new_view())
        else:
            await itx.followup.send(embed=patreon_embed(color=discord.Color.red()), ephemeral=True)



class CallbackModalButton(ui.Button):
    def __init__(self, modal_type: Type[CallbackModal], modal_callback: Callable, **kwargs):
        super(CallbackModalButton, self).__init__(**kwargs)
        self.modal_type = modal_type
        self.modal_callback = modal_callback

    async def callback(self, itx: discord.Interaction) -> None:
        await itx.response.send_modal(self.modal_type(self.modal_callback))