from contextvars import ContextVar
import yoyo
import pathlib
import asyncpg
import logging
from urllib.parse import urlparse

log = logging.getLogger(__name__)
ctx_connection = ContextVar("ctx_connection")
ctx_transaction = ContextVar("ctx_transaction")



async def create_db(dsn: str, database_name: str, owner: str):
    conn = await asyncpg.connect(dsn + "/template1")
    try:
        await conn.execute(f"create database {database_name} owner {owner};")
        await conn.close()
    except asyncpg.DuplicateDatabaseError:
        await conn.close()
        log.debug(f"Skipped Database Creation. {database_name} already created.")

class DbProxy:
    """For later expansion"""
    def __init__(self, connection: asyncpg.Connection):
        self.connection = connection

    def __await__(self):
        return self.connection.__await__()


class Pg:


    @classmethod
    async def create_tables(cls, dsn: str, database_name: str, migrations_path: pathlib.Path):
        dsn_parts = urlparse(dsn)
        owner = dsn_parts.username
        migrations_folder = str(migrations_path)
        await create_db(dsn, database_name, owner)
        migrations = yoyo.read_migrations(migrations_folder)
        backend = yoyo.get_backend(dsn + f"/{database_name}")
        log.debug(f"Running migrations on {database_name}")
        with backend.lock():
            backend.apply_migrations(backend.to_apply(migrations))
        backend.connection.close()
        log.debug("Migrations complete")
        pool = await asyncpg.create_pool(dsn + f"/{database_name}")
        return cls(pool)

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool



    async def __aenter__(self) -> DbProxy:
        self._conn = await self.pool.acquire()
        self._trans = self._conn.transaction()
        await self._trans.start()
        ctx_connection.set(self._conn)
        ctx_transaction.set(self._trans)
        return DbProxy(self._conn)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        conn = ctx_connection.get()
        trans = ctx_transaction.get()
        if exc_type:
            await trans.rollback()
        else:
            await trans.commit()
        try:
            await conn.close()
        except:
            pass