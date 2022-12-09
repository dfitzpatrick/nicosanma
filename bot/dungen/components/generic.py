from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional, Union, TYPE_CHECKING
from uuid import uuid4

import asyncpg
import discord
from discord import ui

from bot.dungen import config_constants
from bot.dungen.components.buttons import UpscaleButton, FinalizeButton
from bot.dungen.components.modals import SeedModal
from bot.dungen.components.selects import SingleSelect
from bot.dungen.services import update_persistant_view, text_timedelta

if TYPE_CHECKING:
    from bot.bot import DungenBot

log = logging.getLogger(__name__)


class GeneratedMapView(ui.View):
    message: Optional[Union[discord.Message, discord.PartialMessage]] = None
    result_embed_cache: Optional[discord.Embed] = None

    def __init__(self,
                 bot: DungenBot,
                 theme_options: List[discord.SelectOption],
                 size_options: List[discord.SelectOption],
                 message: Optional[Union[discord.Message, discord.PartialMessage]] = None,
                 custom_id_prefix: str = str(uuid4()),
                 default_theme: Optional[str] = None,
                 default_size: Optional[str] = None,
                 download_url: Optional[str] = None,
                 tile_size: int = config_constants.TILE_SIZE_REGULAR,
                 seed: str = "random",
                 seed_editable=True,
                 seed_edited=False,
                 regenerated=False,
                 user_id: Optional[int] = None,
                 guild_id: Optional[int] = None,
                 user_display_name: Optional[str] = None,
                 user_avatar_url: Optional[str] = None,
                 finalized: bool = False,
                 upscaled: bool = False,
                 **kwargs
                 ):
        log.debug(f"Sending kwargs to super {kwargs}")
        super(GeneratedMapView, self).__init__(**kwargs)
        log.debug(f"Timeout is now {self.timeout}")
        if getattr(self, 'designation') is None:
            self.designation = 'generic'
        self.user_id = user_id
        self.user_display_name = user_display_name
        self.user_avatar_url = user_avatar_url
        self.guild_id = guild_id
        self.upscaled = upscaled
        self.finalized = finalized
        self.message = message
        self.bot = bot
        self.download_url = download_url
        self.custom_id_prefix = custom_id_prefix
        self.regenerated = regenerated
        self.theme_select = SingleSelect(
            theme_options,
            placeholder="Select Theme",
            default_value=default_theme if self.regenerated else None,
            custom_id=f"{custom_id_prefix}_generated_map_theme"
        )
        self.size_select = SingleSelect(
            size_options,
            default_value=default_size,
            custom_id=f"{custom_id_prefix}_generated_map_size"
        )
        self.seed_edited = seed_edited
        log.debug(f"Regenerated: {self.regenerated}")
        log.debug(f"Seed Edited: {self.seed_edited}")
        if self.regenerated or self.seed_edited:
            log.debug(f"Setting seed to {seed}")
            self.seed = seed
        else:
            self.seed = self.default_seed
        self.tile_size = tile_size

        self.seed_button = ui.Button(
            label=f"Change Seed ({self.seed.capitalize()})",
            style=discord.ButtonStyle.blurple,
            row=4,
            custom_id=f"{custom_id_prefix}_generated_map_seed"
        )
        self.seed_button.callback = self.seed_button_callback

        self.add_item(self.theme_select)
        self.add_item(self.size_select)

        if self.regenerated:
            self.btn_upscale = self.add_upscale_button()

        if seed_editable and not self.regenerated:
            log.debug(f"Seed editable: {seed_editable}")
            log.debug(f"Regenerated: {self.regenerated}")
            self.add_item(self.seed_button)

    @property
    def applying_theme_embed(self):
        embed = discord.Embed(
            title="Applying Your Settings",
            description="Please wait. This may take a moment while the image generates"
        )
        embed.set_author(
            name=config_constants.SERVICE_NAME,
            url=config_constants.PATREON_URL,
            icon_url=config_constants.SERVICE_ICON
        )
        return embed

    def add_upscale_button(self):
        label = "Upscale & Finalize"
        btn_upscale = UpscaleButton(
            always_allow=False,
            label=label,
            style=discord.ButtonStyle.red,
            row=4,
            custom_id=f"{self.custom_id_prefix}_generated_{self.designation}_upscale",
            pre_hook=self.on_upscale
        )
        self.add_item(btn_upscale)
        return btn_upscale

    def handle_finalized(self):
        if self.finalized and self.download_url:
            self.remove_children()
            if not self.upscaled:
                self.add_upscale_button()
            self.add_item(ui.Button(
                label="Download",
                url=self.download_url,
                row=4,
            ))
    async def edit_button_status(self, disabled: bool):
        for item in self.children:
            item.disabled = disabled
        await self.message.edit(embed=self.applying_theme_embed, view=self)

    async def send_public_embed(self):
        if self.message is None or self.message.channel is None:
            raise AttributeError("Message/Channel is not found")
        embed: discord.Embed = self.result_embed_cache or await self.generate(finalize=True)

        if self.user_display_name and self.user_avatar_url:
            embed.set_footer(text=f"Created by {self.user_display_name}", icon_url=self.user_avatar_url)
        embed.timestamp = datetime.now(timezone.utc)
        channel = self.message.channel
        view = self.as_new_view()
        view.result_embed_cache = self.result_embed_cache
        message = await channel.send(embed=embed, view=view)
        view.message = message
        async with self.bot.db as db:
            log.debug(f"Adding persistence to new view {view.custom_id_prefix}")
            await view.update_persistent_view(db.connection)
        return message

    def remove_children(self):
        for child in self.children:
            self.remove_item(child)

    async def interaction_check(self, itx: discord.Interaction) -> bool:
        result = self.user_id is None or self.user_id == itx.user.id

        if not result:
            embed = discord.Embed(
                title="Uh Oh!",
                description=f"This particular Map/Cave isn't meant for you.",
                color=discord.Color.red()
            )
            await itx.response.send_message(embed=embed, ephemeral=True)
        return result

    async def seed_button_callback(self, itx: discord.Interaction):
        await itx.response.send_modal(SeedModal(self))

    @property
    def default_seed(self):
        return NotImplementedError

    def to_dict(self):
        raise NotImplementedError

    def as_new_view(self, **extras):
        raise NotImplementedError

    async def generate(self, finalize: bool = False):
        raise NotImplementedError

    async def on_upscale(self, interaction: discord.Interaction, button: FinalizeButton):
        pass

    async def update_persistent_view(self, connection: asyncpg.Connection):
        log.debug(f"Attempting to update persistent view {self.custom_id_prefix}")
        log.debug(f"Message is {self.message}")
        log.debug(f"Timeout is {self.timeout}")
        if self.message is None or self.timeout is not None:
            raise AttributeError("For Persistent views, make sure to attach view.message when sending the initial view and ensure timeout is set to None")
        await update_persistant_view(connection, self.designation, self.message, self.to_dict())
        self.bot.task_debounce.create_task(self.view_timeout(), name=f"view-expiry-{self.custom_id_prefix}")

    async def view_timeout(self, target: Optional[datetime]=None):
        if target is None:
            target = datetime.now() + text_timedelta(config_constants.VIEW_TIMEOUT)
        await discord.utils.sleep_until(target)
        async with self.bot.db as db:
            await self.expire_persistent_view(db.connection)

    async def remove_persistence(self):
        sql = """
                delete from discord_persistent_views
                where view_payload->>'custom_id_prefix' = $1;
                """
        async with self.bot.db as db:
            await db.connection.execute(sql, self.custom_id_prefix)
        log.debug(f"Persistence removed from {self.custom_id_prefix}")

    async def expire_persistent_view(self, connection: asyncpg.Connection):
        await self.remove_persistence()
        log.debug(f"Expiring view {self.custom_id_prefix}")
        log.debug(self.message)
        for child in self.children:
            if child.custom_id is not None:
                # do not disable link buttons
                child.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                log.debug(f"Could not edit message {self.message.id} Message does not exist.")

        self.stop()

    def reschedule_timeout_task(self, target: Optional[datetime] = None):
        self.bot.task_debounce.create_task(self.view_timeout(target), name=f"view-expiry-{self.custom_id_prefix}")
