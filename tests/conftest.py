import pathlib
import os
from typing import Union

import pytest
import pytest_asyncio
import asyncpg
import yoyo
import asyncio

from bot.db import Pg

dsn_base = f"postgresql://{os.environ['DB_USER']}:{os.environ['DB_PWD']}" + \
               f"@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}"

test_prefix = "tmpnico"
test_db = f"{test_prefix}_db"
test_db_template = f"{test_prefix}_template"
MIGRATIONS = pathlib.Path(__file__).parents[1] / 'migrations'

@pytest.fixture(scope="session")
def event_loop():
    loop = None
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    finally:
        return loop


@pytest_asyncio.fixture(scope="session")
async def session_test():
    test_dsn = dsn_base + "/template1"
    conn = await asyncpg.connect(test_dsn)
    await conn.execute(f"DROP DATABASE IF EXISTS {test_db_template} WITH (FORCE);")
    await conn.execute(f"CREATE DATABASE {test_db_template} OWNER {os.environ['DB_USER']};")
    await conn.close()
    backend = yoyo.get_backend(dsn_base + "/" + test_db_template)
    migrations = yoyo.read_migrations(str(MIGRATIONS))
    with backend.lock():
        backend.apply_migrations(backend.to_apply(migrations))
    backend.break_lock()
    backend.connection.close()
    yield

@pytest_asyncio.fixture()
async def db_reset(session_test):
    conn = await asyncpg.connect(dsn_base + "/template1")
    await conn.execute(f"DROP DATABASE IF EXISTS {test_db} WITH (FORCE);")
    await conn.execute(f"CREATE DATABASE {test_db} WITH TEMPLATE {test_db_template} OWNER {os.environ['DB_USER']};")
    await conn.close()
    yield

@pytest_asyncio.fixture()
async def db_conn(db_reset):
    conn = await asyncpg.connect(dsn_base + "/" + test_db)
    yield conn

@pytest_asyncio.fixture()
async def db_pool(db_reset):
    pool = await asyncpg.create_pool(dsn_base + "/" + test_db)
    yield pool
    await pool.close()

@pytest_asyncio.fixture()
async def pg(db_pool):
    pg = Pg(db_pool)
    yield pg
