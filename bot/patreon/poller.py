from __future__ import annotations

import asyncpg
from discord.ext import tasks
import os

import aiohttp
from typing import TYPE_CHECKING, List, Any, Union, TypedDict, Dict, Optional, Tuple
import logging
if TYPE_CHECKING:
    from bot.db import Pg

DataKey = List[Dict[str, Any]]
IncludedKey = List[Dict[str, Any]]
log = logging.getLogger(__name__)


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


class PatreonPoller:

    def __init__(self, pg: Pg, interval: int = 10):
        self.interval = interval
        self.pg = pg
        self.poller = tasks.loop(minutes=interval, reconnect=True)(self.poller)

    async def start(self):
        log.info(f"Patreon Polling started. {self.interval} minute intervals")
        await self.poller.start()

    def stop(self):
        log.info("Patreon Polling stopped")
        self.poller.stop()

    async def fetch_patreon_payload(self, target: str):
        token = os.environ['PATREON_TOKEN']
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        log.debug(f"Patreon Polling {target}")
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(target) as response:
                response = await response.json()
                return response

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


