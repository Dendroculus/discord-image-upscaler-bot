import discord
from discord import app_commands
from discord.ext import commands

"""
UpScale.py

Cog exposing a single slash command to submit an image for AI upscaling.

Logic flow:
1. Command validation ensures the provided Attachment is an image.
2. Defer the interaction response (thinking) to give time to enqueue the job.
3. Add a job to the database with the user, channel, image URL, and chosen model.
4. Inform the user that the job was queued and provide the job id.

This cog delegates actual processing to a worker process which pulls jobs
from the database and performs the upscaling.
"""

class UpscaleCog(commands.Cog):
    """
    Cog that exposes the /upscale command.

    The command:
    - Accepts an image attachment and a model type choice,
    - Validates the attachment is an image,
    - Enqueues a job in the database and reports the job id back to the user.
    """

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
        """
        Handle the /upscale command.

        Steps:
        1. Validate that the attachment's content_type starts with 'image/'.
        2. Defer the response to acknowledge processing.
        3. Add a job record to the database.
        4. Follow up to tell the user the job id and that processing is underway.
        """
        if not image.content_type or not image.content_type.startswith("image/"):
            return await interaction.response.send_message("❌ Image files only.", ephemeral=True)

        await interaction.response.defer(thinking=True)
        
        _ = await self.bot.db.add_job(
            user_id=interaction.user.id,
            channel_id=interaction.channel_id,
            image_url=image.url,
            model_type=type.value
        )

        await interaction.followup.send(
            "(●'◡'●) I'm UpScaling your image. I'll send the upscaled image here when it's done!"
        )

async def setup(bot):
    """
    Add the UpscaleCog to the bot.
    """
    await bot.add_cog(UpscaleCog(bot))