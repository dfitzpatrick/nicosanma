from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone, timedelta

import asyncpg
import pydantic
from discord.ext import tasks
import os

import aiohttp
from typing import TYPE_CHECKING, List, Any, Union, TypedDict, Dict, Optional, Tuple
import logging

from pydantic import BaseModel

if TYPE_CHECKING:
    from bot.db import Pg

DataKey = List[Dict[str, Any]]
IncludedKey = List[Dict[str, Any]]
log = logging.getLogger(__name__)

PATREON_CLIENT_ID=os.environ.get('PATREON_CLIENT_ID')
PATREON_SECRET=os.environ.get('PATREON_SECRET')
PATREON_MANUAL_REFRESH_TOKEN=os.environ.get('PATREON_MANUAL_REFRESH_TOKEN', '')


class MemberInfo(TypedDict):
    id: int
    active: bool


class MemberTiers(TypedDict):
    id: int
    tiers: List[int]

class MemberConnection(TypedDict):
    patreon_id: int
    provider_name: str
    provider_id: str
    url: Optional[str]

class PatreonTokenPayload(BaseModel):
    access_token: str
    expires_in: int
    token_type: str
    scope: str
    refresh_token: str
    version: str

class NoTokenError(Exception):
    pass


class PatreonToken:

    def __init__(self, pg: Pg):
        self.pg = pg
        self.data: Optional[PatreonTokenPayload] = None
        self.token_url = 'https://www.patreon.com/api/oauth2/token'
        self.issued_at: Optional[datetime] = None
        self.provider_name = 'patreon'

    @property
    def requires_refresh(self):
        seconds_buffer = 10
        if self.issued_at is None or self.data is None:
            return True
        now = datetime.now(timezone.utc)
        return now > self.issued_at + timedelta(seconds=self.data.expires_in - seconds_buffer)

    async def get_access_token(self, from_manual_refresh=False):
        if from_manual_refresh:
            log.debug("Grabbing from manual refresh due to flag set on get_access_token")
            await self.refresh(PATREON_MANUAL_REFRESH_TOKEN)
        if self.requires_refresh:
            await self._load_stored()
            await self.refresh(PATREON_MANUAL_REFRESH_TOKEN if self.data is None else self.data.refresh_token)
        if self.data is None:
            raise NoTokenError
        log.debug(f"get_access_token data {self.data}")
        return self.data.access_token

    async def _load_stored(self) -> asyncpg.Record:
        await asyncio.sleep(2)
        log.debug("Loading token information from database")
        q = "select payload, issued_at from application_tokens where provider_name = $1"
        async with self.pg as db:
            row = await db.connection.fetchrow(q, self.provider_name)
            if row is not None:
                log.debug(row)
                try:
                    data = json.loads(row['payload'])
                    if 'error' not in data.keys():
                        self.data = PatreonTokenPayload(**data)
                        self.issued_at = row['issued_at']
                except pydantic.ValidationError:
                    log.debug(f"{data} is not a valid patreon Token Payload")

    async def refresh(self, manual_refresh_token: Optional[str] = None, retried: bool = False):
        refresh_token = self.data.refresh_token if manual_refresh_token is None else manual_refresh_token,
        log.debug(f"Attempting refresh of token using refresh_token {refresh_token}")
        payload = {
            'grant_type': 'refresh_token',
            'refresh_token':refresh_token,
            'client_id': PATREON_CLIENT_ID,
            'client_secret': PATREON_SECRET
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        log.debug(f"Calling Post to {self.token_url} headers={headers}")
        log.debug(f"Payload: {payload}")
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(self.token_url, data=payload) as resp:

                log.debug(resp)
                data = await resp.json()
                log.debug(data)
                if 'error' not in data.keys():
                    self.issued_at = datetime.now(timezone.utc)
                    self.data = PatreonTokenPayload(**data)
                    log.debug(f"Response: {data}")
                    await self.save()
                else:
                    if retried:
                        raise NoTokenError
                    log.debug("Bad response from refresh request. Not saving")
                    await self.refresh(PATREON_MANUAL_REFRESH_TOKEN, retried=True)


    async def save(self):
        log.debug(f"Saving response to database {self.data}")
        q = """
        insert into application_tokens (provider_name, payload, issued_at)
        values ($1, $2, $3)
        on conflict (provider_name)
        do
            update set payload = $2, issued_at = $3
        """
        async with self.pg as db:
            serialized_data = self.data.json()
            await db.connection.execute(q, "patreon", serialized_data, self.issued_at)




class PatreonPoller:

    def __init__(self, pg: Pg, interval: int = 25):
        self.interval = interval
        self.pg = pg
        self.poller = tasks.loop(minutes=interval, reconnect=True)(self.poller)
        self.token_manager = PatreonToken(pg)

    def start(self):
        log.info(f"Patreon Polling started. {self.interval} minute intervals")
        self.poller.start()

    def stop(self):
        log.info("Patreon Polling stopped")
        self.poller.stop()

    async def fetch_patreon_payload(self, target: str, retried: bool = False):
        token = await self.token_manager.get_access_token(from_manual_refresh=retried)
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        log.debug(f"Patreon Polling {target}")
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(target) as response:
                    response = await response.json()
                    return response
        except aiohttp.ClientResponseError:
            await self.fetch_patreon_payload(target, retried=True)
            if retried:
                raise



    async def fetch_patreon_results(self) -> Tuple[DataKey, IncludedKey]:
        target = "https://www.patreon.com/api/oauth2/v2/campaigns/2442702/members?include=currently_entitled_tiers,user&fields%5Buser%5D=social_connections,full_name,url&fields%5Bmember%5D=patron_status&fields%5Btier%5D=title"
        data = []
        included = []
        while True:
            results = await self.fetch_patreon_payload(target)
            data.extend(results['data'])
            included.extend(results['included'])
            target = results.get('links', {}).get('next')
            if target is None:
                break
        return data, included

    async def _update_patreon_members(self, conn: asyncpg.Connection, payload: List[Dict[str, Union[str, bool]]]):
        """

        Parameters
        ----------
        payload
            A List of type Dict that has
                id: str The patreon member id
                active: bool The status of the member
        -------

        """

        sql = """
            insert into patreons (patreon_id, active)
            values ($1, $2)
            on conflict (patreon_id)
            do
                update set active = $2
        """
        for member in payload:
            await conn.execute(sql, member['id'], member['active'])

    def _format_patreon_members(self, data: List[Dict[str, Any]]) -> List[MemberInfo]:
        container = []
        for member in data:
            member_id = member.get('relationships', {}).get('user', {}).get('data', {}).get('id')
            active = member['attributes']['patron_status'] == 'active_patron'
            if member_id is None:
                continue
            container.append({
                'id': int(member_id),
                'active': active
            })
        return container

    def _extract_member_id_from_data(self, member: Dict[str, Any]) -> Optional[int]:
        member_id = member.get('relationships', {}).get('user', {}).get('data', {}).get('id')
        return self._convert_member_id(member_id)


    def _convert_member_id(self, member_id: str) -> Optional[int]:
        try:
            return int(member_id)
        except (ValueError, TypeError):
            return


    def _format_member_tiers(self, data: List[Dict[str, Any]]) -> List[MemberTiers]:
        container = []
        for member in data:
            member_id = self._extract_member_id_from_data(member)
            if member_id is None:
                continue
            tiers = member.get('relationships', {}).get('currently_entitled_tiers', {}).get('data', [])
            tiers = [int(t['id']) for t in tiers]
            container.append(MemberTiers(id=member_id, tiers=tiers))
        return container

    def _format_member_connections(self, included_data: List[Dict[str, Any]]) -> List[MemberConnection]:
        connections = []
        for member in included_data:
            member_id = self._convert_member_id(member['id'])
            if member_id is None:
                continue
            platforms = member.get('attributes', {}).get('social_connections', {})
            for platform in platforms.keys():
                if platforms[platform] is None:
                    continue
                connections.append(MemberConnection(
                    patreon_id=member_id,
                    provider_name=platform,
                    provider_id=platforms[platform]['user_id'],
                    url=platforms[platform]['url']
                ))
        return connections

    async def _update_patreon_tiers(self, conn: asyncpg.Connection, tiers: List[MemberTiers]):
        flattened_values = [
            (mt['id'], tier)
            for mt in tiers
            for tier in mt['tiers']
        ]
        sql = "insert into patreon_tiers (patreon_id, tier_id) values ($1, $2);"
        await conn.execute("delete from patreon_tiers;")
        await conn.executemany(sql, flattened_values)

    async def _update_patreon_connections(self, conn: asyncpg.Connection, connections: List[MemberConnection]):
        values = [(c['patreon_id'], c['provider_name'], c['provider_id'], c['url']) for c in connections]
        sql = "insert into patreon_social_connections (patreon_id, provider_name, provider_id, url) values ($1, $2, $3, $4);"
        await conn.execute("delete from patreon_social_connections;")
        await conn.executemany(sql, values)

    async def poller(self):
        log.debug("Patreon Poller updating")
        data, included = await self.fetch_patreon_results()
        members = self._format_patreon_members(data)
        tiers = self._format_member_tiers(data)
        connections = self._format_member_connections(included)
        async with self.pg as db:
            await self._update_patreon_members(db.connection, members)
            await self._update_patreon_tiers(db.connection, tiers)
            await self._update_patreon_connections(db.connection, connections)


