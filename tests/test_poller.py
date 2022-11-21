import pytest
from bot.db import Pg, DbProxy
from bot.patreon.poller import PatreonPoller
from .sampledata import patreon_payload, included_payload

@pytest.mark.asyncio
async def test_patreon_members(pg):
    poller = PatreonPoller(pg, 100)
    members = poller._format_patreon_members(patreon_payload)
    assert len(members) == 20

@pytest.mark.asyncio
async def test_patreon_member_tiers(pg):
    poller = PatreonPoller(pg, 100)
    member_tiers = poller._format_member_tiers(patreon_payload)
    assert len(member_tiers) == 20
    assert member_tiers[1]['tiers'][0] == 3313135

@pytest.mark.asyncio
async def test_poller_update_patreon_members(pg):
    poller = PatreonPoller(pg, 100)
    members = poller._format_patreon_members(patreon_payload)
    async with poller.pg as db:
        await poller._update_patreon_members(db.connection, members)
        count = await db.connection.fetchval("select count(id) from patreons")
        assert count == 20

@pytest.mark.asyncio
async def test_poller_update_patreon_tiers(pg):
    poller = PatreonPoller(pg, 100)
    members = poller._format_patreon_members(patreon_payload)
    tiers = poller._format_member_tiers(patreon_payload)
    async with poller.pg as db:
        await poller._update_patreon_members(db.connection, members)
        await poller._update_patreon_tiers(db.connection, tiers)
        count = await db.connection.fetchval("select count(patreon_id) from patreon_tiers")
        assert count == 3


@pytest.mark.asyncio
async def test_patreon_connections(pg):
    poller = PatreonPoller(pg, 100)
    connections = poller._format_member_connections(included_payload)
    assert isinstance(connections[0]['patreon_id'], int)
    assert len(connections) == 9


@pytest.mark.asyncio
async def test_poller_update_patreon_connections(pg):
    poller = PatreonPoller(pg, 100)
    members = poller._format_patreon_members(patreon_payload)
    tiers = poller._format_member_tiers(patreon_payload)
    connections = poller._format_member_connections(included_payload)
    async with poller.pg as db:
        await poller._update_patreon_members(db.connection, members)
        await poller._update_patreon_tiers(db.connection, tiers)
        await poller._update_patreon_connections(db.connection, connections)
        count = await db.connection.fetchval("select count(patreon_id) from patreon_social_connections")
        assert count == 9

