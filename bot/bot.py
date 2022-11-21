from __future__ import annotations

import json
from datetime import datetime, timezone

import discord
from discord.ext import commands
import os
from bot.db import Pg
import asyncpg
import pathlib
from typing import TYPE_CHECKING, Optional, Dict, Any, List

from bot.dungen.components.views import DungenGenerateView, CaveGeneratedView
from bot.dungen import choices, config_constants
from bot.dungen.services import update_persistant_view, text_timedelta
from bot.patreon.poller import PatreonPoller
from functools import partial
import logging

from bot.scheduling import TaskDebounce

if TYPE_CHECKING:
    from bot.dungen.components.generic import GeneratedMapView
migrations = pathlib.Path(__file__).parents[1] / 'migrations'

log = logging.getLogger(__name__)

class DungenBot(commands.Bot):
    db: Pg
    patreon_polling: PatreonPoller
    task_debounce: TaskDebounce

    def __init__(self, **kwargs):
        super(DungenBot, self).__init__(**kwargs)

    async def setup_hook(self) -> None:
        self.db = await Pg.create_tables(os.environ['DSN'], database_name=config_constants.PRODUCTION_DATABASE_NAME, migrations_path=migrations)
        self.patreon_polling = PatreonPoller(self.db, interval=1)
        self.task_debounce = TaskDebounce()
        async with self.db as db:
            records = await db.connection.fetch("select * from discord_persistent_views")
        records = await self.cleanup_persistent_views(records)
        await self.load_persistent_views(records)
        for view in self.persistent_views:
            if hasattr(view, 'reschedule_timeout_task'):
                view.reschedule_timeout_task()

    def find_partial_message_from_db(self, record: Dict[str, Any]) -> Optional[discord.PartialMessage]:
        guild_id = record['guild_id']
        channel_id = record['channel_id']
        message_id = record['message_id']

        channel = self.get_partial_messageable(channel_id, guild_id=guild_id)
        if channel is None:
            return
        message = channel.get_partial_message(message_id)
        return message

    def persistent_record_to_view(self, record: Dict[str, Any]) -> Optional[GeneratedMapView]:
        designations = {
            'map': partial(DungenGenerateView, bot=self, theme_options=choices.DUNGEN_THEME_OPTIONS,
                           size_options=choices.DUNGEON_SIZE_OPTIONS),
            'cave': partial(CaveGeneratedView, bot=self, theme_options=choices.CAVE_THEME_OPTIONS,
                            size_options=choices.CAVE_SIZE_OPTIONS)
        }
        view_cls = designations.get(record['designation'])
        message = self.find_partial_message_from_db(record)
        log.debug(f"View class: {view_cls}")
        log.debug(f"message: {message}")
        if view_cls is None or message is None:
            return
        payload = json.loads(record['view_payload'])
        view = view_cls(timeout=None, **payload)
        view.message = message
        return view

    async def cleanup_persistent_views(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Called to help clear the database of any views that might have expired when the bot was offline.
        This also reschedules the expiry tasks
        """
        expired: List[GeneratedMapView] = []
        not_found: List[Dict[str, Any]] = []
        new_records = []
        for r in records:
            expiry_delta = text_timedelta(config_constants.VIEW_TIMEOUT)
            expiration = r['updated'] + expiry_delta
            if datetime.now(timezone.utc) >= expiration:
                view = self.persistent_record_to_view(r)
                if view is not None:
                    expired.append(view)
                else:
                    not_found.append(r)
            else:
                new_records.append(r)
        async with self.db as db:
            sql = "delete from discord_persistent_views where id = $1;"
            for v in expired:
                await v.expire_persistent_view(db.connection)
            for record in not_found:
                log.debug(f"Removing Persistent View Record of {record['id']}")
                await db.connection.execute(sql, record['id'])
        return new_records

    async def load_persistent_views(self, records: List[Dict[str, Any]]):
        cleanup = []
        for r in records:
            view = self.persistent_record_to_view(r)
            if view is None:
                log.error("Unknown designation or no message in view. Deleting")
                cleanup.append(r)
                continue
            log.info(f"Adding Persistent View for Message {view.message.id} with custom id {view.custom_id_prefix}")
            try:
                for child in view.children:
                    log.debug(child.custom_id)
                self.add_view(view, message_id=r['message_id'])
            except ValueError as e:
                log.error(f"View Message {r['message_id']}was not a valid persistent view. Queing to remove")
                log.error(e)
                cleanup.append(r)
                continue

        async with self.db as db:
            for record in cleanup:
                log.debug(f"found stale persistent view from Guild {record['guild_id']}. Removing ")
                await db.connection.execute("delete from discord_persistent_views where id = $1", record['id'])


