import asyncpg

from bot.dungen.services import *
import pytest
import random
class ID:
    @property
    def id(self):
        return random.randint(2345352352355,63263636346326346)

class MessageMock:

    def __init__(self, message_id = None):
        self.message_id = message_id

    @property
    def guild(self):
        return ID()

    @property
    def channel(self):
        return ID()

    @property
    def id(self):
        return self.message_id or random.randint(2345352352355, 63263636346326346)


@pytest.mark.asyncio
async def test_persistent_views(db_conn: asyncpg.Connection):
    sample_payload = {'a': 1, 'b': 2, 'c': 3}
    message = MessageMock()
    await update_persistant_view(db_conn, "map", message, sample_payload)
    v = await db_conn.fetchval("select count(id) from discord_persistent_views")
    assert v == 1


@pytest.mark.asyncio
async def test_upsert_works(db_conn: asyncpg.Connection):
    sample_payload = {'a': 1, 'b': 2, 'c': 3}
    message = MessageMock(123456789)
    await update_persistant_view(db_conn, "map", message, sample_payload)
    new_payload = {'a': 2, 'b': 2, 'c': 3}
    await update_persistant_view(db_conn, "map", message, new_payload)
    v = await db_conn.fetchval("select count(id) from discord_persistent_views")
    assert v == 1
    data = await db_conn.fetch("select * from discord_persistent_views", )
    payload = data[0]['view_payload']
    payload = json.loads(payload)
    assert payload['a'] == 2
