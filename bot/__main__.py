import asyncpg
import discord
import os
from discord.ext import commands
import asyncio
import logging

from bot.bot import DungenBot

log = logging.getLogger(__name__)

extensions = (
    'bot.core',
    'bot.dungen.cog',
)


class MissingConfigurationException(Exception):
    pass


def assert_envs_exist():
    envs = (
        ('TOKEN', 'The Bot Token', str),
        ('DSN', 'The DSN Connection String for Postgresql without the database. Ex: postgresql://postgres:postgres@localhost:5434 ', str),
        ('PATREON_TOKEN', 'Patreon Creators Token for Background Tasks', str),
    )

    for e in envs:
        ident = f"{e[0]}/{e[1]}"
        value = os.environ.get(e[0])
        if value is None:
            raise MissingConfigurationException(f"{ident} needs to be defined")
        try:
            _ = e[2](value)
        except ValueError:
            raise MissingConfigurationException(f"{ident} is not the required type of {e[2]}")


async def entry_point():
    assert_envs_exist()

    pool = asyncpg.create_pool(os.environ['DSN'])
    token = os.environ['TOKEN']
    intents = discord.Intents.all()
    intents.message_content = True
    intents.members = True
    bot = DungenBot(
        pg_pool=pool,
        intents=intents,
        command_prefix='!',
        slash_commands=True,
    )
    async with bot:
        try:
            for ext in extensions:
                await bot.load_extension(ext)
                log.debug(f"Extension {ext} loaded")

            await bot.start(token)
        finally:
            await bot.close()


try:
    asyncio.run(entry_point())
except KeyboardInterrupt:
    pass

