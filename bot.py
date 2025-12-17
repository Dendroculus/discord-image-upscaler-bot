import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from database import Database
from utils.PatchFix import patch_torchvision

load_dotenv()
patch_torchvision()

class UpscaleBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix=None, intents=intents)
        self.db = Database()
        self.initial_extensions = [
            "cogs.upscale", 
            "cogs.delivery"
        ]

    async def setup_hook(self):
        await self.db.connect()
        await self.db.init_schema()
        
        for ext in self.initial_extensions:
            await self.load_extension(ext)
            
        await self.tree.sync()
        print("🚀 Bot is clean and online!")

    async def close(self):
        await self.db.close()
        await super().close()

if __name__ == "__main__":
    bot = UpscaleBot()
    bot.run(os.getenv("DISCORD_TOKEN"))