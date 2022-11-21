from __future__ import annotations
import asyncio
from abc import ABC
from datetime import datetime
from typing import List, Optional, Union, TYPE_CHECKING
from uuid import uuid4

import asyncpg
import discord
from discord import ui

from bot.dungen import config_constants
from bot.dungen.components.buttons import UpscaleButton
from bot.dungen.components.modals import SeedModal
from bot.dungen.components.selects import SingleSelect
from bot.dungen.services import update_persistant_view, text_timedelta
import logging
if TYPE_CHECKING:
    from bot.bot import DungenBot

log = logging.getLogger(__name__)





class GeneratedMapView(ui.View):
    message: Optional[Union[discord.Message, discord.PartialMessage]] = None

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
                 regenerated=False,
                 **kwargs
                 ):

        super(GeneratedMapView, self).__init__(**kwargs)
        self.designation = 'generic'
        self.message = message
        self.bot = bot
        self.download_url = download_url
        self.custom_id_prefix = custom_id_prefix
        self.theme_select = SingleSelect(
            theme_options,
            default_value=default_theme,
            custom_id=f"{custom_id_prefix}_generated_map_theme"
        )
        self.size_select = SingleSelect(
            size_options,
            default_value=default_size,
            custom_id=f"{custom_id_prefix}_generated_map_size"
        )
        self.seed = seed
        self.tile_size = tile_size
        self.regenerated = regenerated
        self.seed_button = ui.Button(
            label=f"Change Seed ({self.seed.capitalize()})",
            style=discord.ButtonStyle.blurple,
            row=4,
            custom_id=f"{custom_id_prefix}_generated_map_seed"
        )
        self.seed_button.callback = self.seed_button_callback

        self.add_item(self.theme_select)
        self.add_item(self.size_select)

        btn_upscale = UpscaleButton(
            always_allow=False,
            label="Upscale (Patreon)",
            style=discord.ButtonStyle.red,
            row=4,
            custom_id=f"{custom_id_prefix}_generated_map_upscale"
        )
        if self.regenerated:
            self.add_item(btn_upscale)

        if seed_editable:
            self.add_item(self.seed_button)
        if download_url:
            self.add_item(ui.Button(
                label="Download",
                url=download_url,
                row=4,
            )
            )

    async def seed_button_callback(self, itx: discord.Interaction):
        await itx.response.send_modal(SeedModal(self))

    def to_dict(self):
        raise NotImplementedError

    def as_new_view(self, **extras):
        raise NotImplementedError

    async def generate(self):
        raise NotImplementedError

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

    async def expire_persistent_view(self, connection: asyncpg.Connection):
        sql = """
        delete from discord_persistent_views
        where view_payload->>'custom_id_prefix' = $1;
        """
        log.debug(f"Expiring view {self.custom_id_prefix}")
        log.debug(self.message)
        for child in self.children:
            if child.custom_id is not None:
                # do not disable link buttons
                child.disabled = True
        if self.message is not None:
            await self.message.edit(view=self)

        async with self.bot.db as db:
            await db.connection.execute(sql, self.custom_id_prefix)
        self.stop()

    def reschedule_timeout_task(self, target: Optional[datetime] = None):
        self.bot.task_debounce.create_task(self.view_timeout(target), name=f"view-expiry-{self.custom_id_prefix}")
