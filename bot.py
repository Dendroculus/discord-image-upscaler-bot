from utils.PatchFix import patch_torchvision
import os
import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv
from utils.AutoDelete import delete_stored_images

from database import Database

load_dotenv()
    
patch_torchvision()

class UpscaleBot(commands.Bot):
    """
    Discord bot responsible for accepting upscale requests, persisting them,
    and delivering completed results back to the originating channel.
    """

    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix=None, intents=intents)
        self.db = Database()
        
    @tasks.loop(seconds=10)
    async def periodic_image_cleanup(self):
        await delete_stored_images(self)

    async def setup_hook(self):
        """Initialize database, sync commands, and start delivery loop."""
        await self.db.connect()
        await self.db.init_schema()
        await self.tree.sync()
        self.check_completed_jobs.start()
        print("Bot online. Ready to accept upscale requests.")

    async def close(self):
        """Gracefully close resources."""
        await self.db.close()
        await super().close()

    @tasks.loop(seconds=5)
    async def check_completed_jobs(self):
        """
        Periodically scan for completed jobs and post results to their channels.
        """
        completed_jobs = await self.db.get_completed_jobs()
        for job in completed_jobs:
            channel_id = job["channel_id"]
            file_path = job["output_path"]
            channel = self.get_channel(channel_id) or await self.fetch_channel(channel_id)

            if not os.path.exists(file_path):
                print(f"⚠️ File missing for job {job['job_id']}: {file_path}")
                await self.db.mark_job_sent(job["job_id"])
                continue

            try:
                await channel.send(
                    content=(
                        f"Upscale complete for <@{job['user_id']}>!\n"
                        f"Mode: `{job['model_type'].capitalize()}`"
                    ),
                    file=discord.File(file_path),
                )
                print(f"📨 Delivered job #{job['job_id']} to channel {channel_id}")
                await self.db.mark_job_sent(job["job_id"])
            except discord.Forbidden:
                print(f"❌ Missing permission to send in channel {channel_id}")
                await self.db.mark_job_sent(job["job_id"])
            except Exception as e:
                print(f"❌ Delivery error for job {job['job_id']}: {e}")

    @check_completed_jobs.before_loop
    async def before_checks(self):
        """Ensure bot is ready before starting loops."""
        await self.wait_until_ready()


bot = UpscaleBot()


@bot.tree.command(name="upscale", description="Upscale an image")
@app_commands.describe(image="Image to upscale", type="AI Model")
@app_commands.choices(
    type=[
        app_commands.Choice(name="General Photo", value="general"),
        app_commands.Choice(name="Anime / Illustration", value="anime"),
    ]
)
async def upscale(
    interaction: discord.Interaction,
    image: discord.Attachment,
    type: app_commands.Choice[str],
):
    """
    Slash command handler that enqueues an upscale job.
    """
    if not image.content_type or not image.content_type.startswith("image/"):
        return await interaction.response.send_message("❌ Image files only.", ephemeral=True)

    await interaction.response.defer(thinking=True)

    job_id = await bot.db.add_job(
        user_id=interaction.user.id,
        channel_id=interaction.channel.id,
        image_url=image.url,
        model_type=type.value,
    )

    await interaction.followup.send(
        f"🧾 Job #{job_id} queued. I’ll post the result here when it’s ready!"
    )


def main():
    """Entry point to run the Discord bot."""
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN is not set in the environment.")
    bot.run(token)


if __name__ == "__main__":
    main()