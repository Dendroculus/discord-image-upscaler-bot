import os
import discord
from discord.ext import commands, tasks

"""
Deliverer.py

Cog responsible for delivering completed upscaling jobs' resulting files to
Discord channels and performing cleanup.

Logic flow:
1. A background task (check_completed_jobs) runs periodically.
2. The task fetches jobs marked as completed from the database.
3. For each job:
   - resolve the channel,
   - verify the output file exists,
   - attempt to send the file to the channel mentioning the user and mode,
   - regardless of delivery outcome, delete the local file and mark the job as sent.
4. A before_loop handler waits until the bot is ready before starting the loop.
"""

class DeliveryCog(commands.Cog):
    """
    Cog that periodically polls for completed jobs and sends results.

    Attributes:
        bot: Reference to the parent bot.
        db: Convenience reference to the bot's Database instance.

    Methods:
        check_completed_jobs: periodic task to deliver files.
        before_checks: wait until bot is ready before loop starts.
    """

    def __init__(self, bot):
        """
        Initialize the delivery cog and start the background delivery loop.
        """
        self.bot = bot
        # Use the bot's database instance for job retrieval and updates.
        self.db = getattr(bot, "db", None)
        self.check_completed_jobs.start()

    def cog_unload(self):
        """
        Cancel the background task when the cog is unloaded.
        """
        self.check_completed_jobs.cancel()

    @tasks.loop(seconds=5)
    async def check_completed_jobs(self):
        """
        Periodic task that:
        - Retrieves completed jobs from the DB,
        - Sends the resulting file to the originating channel,
        - Removes the local file and marks the job as sent to avoid re-delivery.

        The task tolerates:
        - Missing files (marks job sent and logs a warning),
        - Missing channel/send permissions (logs errors but still marks sent).
        """
        completed_jobs = await self.bot.db.get_completed_jobs()
        for job in completed_jobs:
            channel_id = job["channel_id"]
            file_path = job["output_path"]
            channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)

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
        Prevent the delivery loop from starting until the bot is ready.
        """
        await self.bot.wait_until_ready()


async def setup(bot):
    """
    Standard discord.py extension setup function to add this cog.
    """
    await bot.add_cog(DeliveryCog(bot))