from utils.PatchFix import patch_torchvision
import os
import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv
from database import Database

load_dotenv()

patch_torchvision()


"""
bot.py

Discord bot responsible for receiving image upscale requests, persisting them to
the database, and delivering completed results back to the originating channel.

This module exposes the UpscaleBot class and a top-level slash command
implementation for enqueueing jobs. Use `main()` to run the bot process.
"""


class UpscaleBot(commands.Bot):
    """
    Discord bot that handles upscale job lifecycle and delivery.

    Attributes:
        db (Database): Asynchronous database wrapper for job persistence.
    """

    def __init__(self):
        """
        Initialize the bot without a text command prefix and prepare the DB.
        """
        intents = discord.Intents.default()
        super().__init__(command_prefix=None, intents=intents)
        self.db = Database()

    async def setup_hook(self):
        """
        Bot startup hook that prepares the database, synchronizes application
        commands with Discord, and starts background delivery loops.
        """
        await self.db.connect()
        await self.db.init_schema()
        await self.tree.sync()
        self.check_completed_jobs.start()
        print("Bot online. Ready to accept upscale requests.")

    async def close(self):
        """
        Gracefully close the database pool and the underlying bot.
        """
        await self.db.close()
        await super().close()

    @tasks.loop(seconds=5)
    async def check_completed_jobs(self):
        """
        Background loop that polls the database for completed jobs and
        attempts to deliver the resulting image files to the appropriate
        channels. After delivery, the local file is removed and the job is
        marked as sent to prevent duplicate processing.
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
            except discord.Forbidden:
                print(f"❌ Missing permission to send in channel {channel_id}")
            except Exception as e:
                print(f"❌ Delivery error for job {job['job_id']}: {e}")
            finally:
                # Clean up the file and mark as sent regardless of delivery outcome
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        print(f"🗑️ Deleted local file for job #{job['job_id']}: {file_path}")
                    except Exception as cleanup_err:
                        print(f"⚠️ Could not delete file for job #{job['job_id']}: {cleanup_err}")
                await self.db.mark_job_sent(job["job_id"])

    @check_completed_jobs.before_loop
    async def before_checks(self):
        """
        Ensure the bot is fully ready before starting the delivery loop.
        """
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
    Slash command that enqueues an image upscale job.

    The command accepts an attachment and a model type choice, validates the
    input, defers the interaction to gain processing time, persists a job row,
    and notifies the user that their job was queued.
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
        f"(●'◡'●) I'm UpScaling your image. Please wait for a moment, I'll post the result here when it's ready!"
    )


def main():
    """
    Entry point to run the Discord bot process.

    Reads DISCORD_TOKEN from the environment and runs the bot. Raises a
    RuntimeError if the token is not set.
    """
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN is not set in the environment.")
    bot.run(token)


if __name__ == "__main__":
    main()