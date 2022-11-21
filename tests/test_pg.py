import pytest

from bot.db import Pg


@pytest.mark.asyncio
async def test_pg_context_transaction(db_pool):
    pass