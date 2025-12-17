import os
import discord
from discord.ext import commands, tasks

class DeliveryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_completed_jobs.start()

    def cog_unload(self):
        self.check_completed_jobs.cancel()

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

async def setup(bot):
    await bot.add_cog(DeliveryCog(bot))