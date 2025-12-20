import discord
from discord import app_commands
from discord.ext import commands

"""
UpScale.py

Discord Cog that provides an /upscale slash command.

Purpose:
- Accept an image attachment from a user
- Register an upscaling job into the database queue
- Estimate processing and queue wait time
- Inform the user when the job is likely to finish

Notes:
- Uses simple heuristics for time estimation (pixel-based + queue-based)
- Designed to be non-blocking and user-friendly with deferred responses
"""

class UpscaleCog(commands.Cog):
    """
    Cog responsible for image upscaling commands.

    Attributes:
        bot (commands.Bot): The main Discord bot instance.
                              Expected to have `bot.db` with:
                              - add_job(...)
                              - get_queue_position()
    """

    def __init__(self, bot):
        """
        Initialize the UpscaleCog.

        Args:
            bot (commands.Bot): The bot instance this cog is attached to.
        """
        self.bot = bot

    @app_commands.command(name="upscale", description="Upscale an image")
    @app_commands.describe(
        image="Image to upscale",
        type="AI model used for upscaling"
    )
    @app_commands.choices(
        type=[
            app_commands.Choice(name="General Photo", value="general"),
            app_commands.Choice(name="Anime / Illustration", value="anime"),
        ]
    )
    async def upscale(
        self,
        interaction: discord.Interaction,
        image: discord.Attachment,
        type: app_commands.Choice[str]
    ):
        """
        Handle the /upscale slash command.

        Flow:
        1. Validate that the uploaded file is an image
        2. Defer the interaction to allow longer processing
        3. Register the job in the database queue
        4. Estimate processing time based on image resolution
        5. Estimate queue wait time based on jobs ahead
        6. Send the user an estimated completion timestamp

        Args:
            interaction (discord.Interaction): The interaction context.
            image (discord.Attachment): The uploaded image file.
            type (app_commands.Choice[str]): Selected AI upscaling model.
        """

        if not image.content_type or not image.content_type.startswith("image/"):
            return await interaction.response.send_message(
                "❌ Image files only.",
                ephemeral=True
            )

        await interaction.response.defer(thinking=True)

        await self.bot.db.add_job(
            user_id=interaction.user.id,
            channel_id=interaction.channel_id,
            image_url=image.url,
            model_type=type.value
        )
        
        width = image.width
        height = image.height
        
        await interaction.followup.send(
            f"(●'◡'●) I'm UpScaling your image (`{width}x{height}`).\n"
        )

async def setup(bot):
    await bot.add_cog(UpscaleCog(bot))
