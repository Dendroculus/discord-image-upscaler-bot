import discord
from discord import app_commands
from discord.ext import commands
import datetime

"""
UpScale.py
Cog for image upscaling with Smart Time Estimation.
"""

class UpscaleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="upscale", description="Upscale an image")
    @app_commands.describe(image="Image to upscale", type="AI Model")
    @app_commands.choices(
        type=[
            app_commands.Choice(name="General Photo", value="general"),
            app_commands.Choice(name="Anime / Illustration", value="anime"),
        ]
    )
    async def upscale(self, interaction: discord.Interaction, image: discord.Attachment, type: app_commands.Choice[str]):
        if not image.content_type or not image.content_type.startswith("image/"):
            return await interaction.response.send_message("❌ Image files only.", ephemeral=True)

        await interaction.response.defer(thinking=True)
        
        _ = await self.bot.db.add_job(
            user_id=interaction.user.id,
            channel_id=interaction.channel_id,
            image_url=image.url,
            model_type=type.value
        )

        
        width = image.width or 1920
        height = image.height or 1080
        total_pixels = width * height
        
        overhead_seconds = 10.0       
        seconds_per_million_px = 20.0 
        
        my_processing_time = overhead_seconds + ((total_pixels / 1_000_000) * seconds_per_million_px)

        queue_count = await self.bot.db.get_queue_position()
        
        jobs_ahead = max(0, queue_count - 1)
        
        wait_time_from_queue = jobs_ahead * 45
        
        total_wait_seconds = wait_time_from_queue + my_processing_time
        
        future_time = datetime.datetime.now() + datetime.timedelta(seconds=total_wait_seconds)
        timestamp = int(future_time.timestamp())

        await interaction.followup.send(
            f"(●'◡'●) I'm UpScaling your image (`{width}x{height}`).\n"
            f"Jobs ahead: **{jobs_ahead}**\n"
            f"Estimated completion: <t:{timestamp}:R>!"
        )

async def setup(bot):
    await bot.add_cog(UpscaleCog(bot))