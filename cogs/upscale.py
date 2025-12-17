import discord
from discord import app_commands
from discord.ext import commands

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

        job_id = await self.bot.db.add_job(
            user_id=interaction.user.id,
            channel_id=interaction.channel.id,
            image_url=image.url,
            model_type=type.value,
        )

        await interaction.followup.send(
            f"(●'◡'●) I'm UpScaling your image. Please wait! (Job #{job_id})"
        )

async def setup(bot):
    await bot.add_cog(UpscaleCog(bot))