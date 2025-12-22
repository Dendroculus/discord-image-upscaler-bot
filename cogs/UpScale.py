import discord
from discord import app_commands
from discord.ext import commands
from constants.Emojis import process, customs

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
        
    @staticmethod
    def add_embed_fields(embed: discord.Embed, fields: list[tuple[str, any, bool]]):
        """
        A helper function to add multiple fields to a discord.Embed.
        fields: list of tuples (name,, value, inline)
        """
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

    @app_commands.command(name="upscale", description="Upscale an image")
    @commands.guild_only()
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
            model_type=type.value,
            token=interaction.token,
            application_id=str(interaction.application_id)
        )
        
        width = image.width
        height = image.height
        
        embed = discord.Embed(
            title=f"{customs['paint']} Image Upscaler",
            description="Request received! Adding to queue...",
            color=discord.Color.orange() 
        )
        fields = [
            ("Status", f"{process['queuing']} **Queued**", True),
            ("Model", f"`{type.value.capitalize()}`", True),
            ("Size", f"`{width}x{height}`", True)
        ]
        self.add_embed_fields(embed=embed, fields=fields)
        embed.set_footer(text="Please wait...")

        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(UpscaleCog(bot))