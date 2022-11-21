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

def bot_task_callback(future: asyncio.Future):
    if future.exception():
        raise future.exception()


async def entry_point():
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

