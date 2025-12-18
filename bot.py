import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from database import Database
from utils.PatchFix import patch_torchvision

load_dotenv()
patch_torchvision()

"""
bot.py

Discord bot bootstrap module.

Logic flow:
1. Patch any torchvision compatibility shims early.
2. Create UpscaleBot which:
   - establishes intents and a Database helper,
   - declares initial cog extensions to load.
3. In setup_hook:
   - connect to the database and initialize schema,
   - load configured cogs,
   - sync application commands with Discord,
   - print a ready message.
4. On close, ensure DB is closed before exiting.

This module is intended to be executed as the main process for the bot.
"""

class UpscaleBot(commands.AutoShardedBot):
    """
    Main bot class.

    Attributes:
        db (Database): Database helper used by cogs for job management.
        initial_extensions (list[str]): List of cog module paths to load at startup.

    Logic flow inside the class:
    - __init__: configure discord intents, create Database instance, and list cogs.
    - setup_hook: asynchronously connect and initialize DB, load cogs, sync commands.
    - close: ensure DB is closed before shutting down the bot.
    """

    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix=None, intents=intents)
        self.db = Database()
        self.initial_extensions = [
            "cogs.UpScale",
            "cogs.Deliverer",
        ]

    async def setup_hook(self):
        """
        Called by discord.py when the bot is preparing to connect.

        Steps:
        1. Connect to the Database and ensure tables/schema exist.
        2. Load each extension listed in initial_extensions.
        3. Sync the command tree with Discord to register application commands.
        4. Print a startup message.
        """
        await self.db.connect()
        await self.db.init_schema()

        for ext in self.initial_extensions:
            await self.load_extension(ext)

        await self.tree.sync()
        print("🚀 Bot is clean and online!")

    async def close(self):
        """
        Ensure database connections are closed before shutting down.
        """
        await self.db.close()
        await super().close()


if __name__ == "__main__":
    bot = UpscaleBot()
    bot.run(os.getenv("DISCORD_TOKEN"))