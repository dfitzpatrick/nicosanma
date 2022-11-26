from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING, Type, Callable

import aiohttp
import discord
from discord import ui

from bot.dungen import config_constants
from bot.dungen.services import patreon_embed
from .modals import CallbackModal
from ..cooldown import DungenCooldown

if TYPE_CHECKING:
    from .views import GeneratedMapView
log = logging.getLogger(__name__)

dungen_cooldown = DungenCooldown()


def client_error_embed() -> discord.Embed:
    embed = discord.Embed(
                title="Uh Oh!",
                description="There was a problem sending this request to the server. Contact the DunGen admin. Likely this is the result of Upscaling.",
                color=discord.Color.red()
            )
    return embed


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

        try:
            view.user_id = itx.user.id
            log.debug(f"View now belongs to {view.user_id}")
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
        except aiohttp.ClientResponseError:
            view.tile_size = 70
            await itx.followup.send(embed=client_error_embed(), ephemeral=True)
        finally:
            async with view.bot.db as db:
                await view.update_persistent_view(db.connection)


class UpscaleButton(GenerateButton):

    def __init__(self, always_allow: bool = False, **kwargs):
        emoji = discord.PartialEmoji.from_str("patreon_w:1045163802745905193")
        super(UpscaleButton, self).__init__(emoji=emoji, **kwargs)
        self.always_allow = always_allow

    async def can_upscale(self, discord_id: str) -> bool:
        view: GeneratedMapView = self.view
        discord_id = str(discord_id)
        if self.always_allow:
            return True
        if discord_id in map(str.strip, config_constants.PATREON_OVERRIDE_UPSCALE.split(',')):
            return True
        sql = """
                select count(t.patreon_id) from patreon_tiers t
                left join patreon_social_connections c on c.patreon_id = t.patreon_id
                left join patreons p on t.patreon_id = p.patreon_id
                where p.active = true
                and t.tier_id in (3313110, 7161052)
                and c.provider_name = 'discord'
                and c.provider_id = $1
        """
        async with self.view.bot.db as db:
            count = await db.connection.fetchval(sql, discord_id)
        return count > 0

    async def callback(self, itx: discord.Interaction):
        view: GeneratedMapView = self.view
        view.user_id = itx.user.id
        log.debug(f"View now belongs to {view.user_id}")
        try:
            # In order to catch the right message object
            await itx.response.defer(thinking=False if view.regenerated else True)
            can_upscale = await self.can_upscale(str(itx.user.id))
            if not can_upscale:
                await itx.followup.send(embed=patreon_embed(color=discord.Color.red()), ephemeral=True)
                return
            view.tile_size = 140
            if view.regenerated:
                view.user_id = itx.user.id
                embed = await view.generate()
                await itx.followup.edit_message(itx.message.id, embed=embed, view=view.as_new_view())
            else:
                embed = await view.generate()
                view = view.as_new_view(custom_id_prefix=str(uuid.uuid4()))
                await itx.followup.send(embed=embed, view=view)
                message = await itx.original_response()
                view.message = message
        except aiohttp.ClientResponseError:
            view.tile_size = 70
            await itx.followup.send(embed=client_error_embed(), ephemeral=True)
        finally:
            async with view.bot.db as db:
                await view.update_persistent_view(db.connection)


class CallbackModalButton(ui.Button):
    def __init__(self, modal_type: Type[CallbackModal], modal_callback: Callable, **kwargs):
        super(CallbackModalButton, self).__init__(**kwargs)
        self.modal_type = modal_type
        self.modal_callback = modal_callback

    async def callback(self, itx: discord.Interaction) -> None:
        await itx.response.send_modal(self.modal_type(self.modal_callback))