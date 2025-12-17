import os
import discord

"""
AutoDelete.py

Utility to deliver completed upscaled images and remove local files afterwards.

The primary coroutine `delete_stored_images(bot)` expects a bot instance that
contains a `db` attribute compatible with Database.get_completed_jobs and
Database.mark_job_sent. The routine will attempt to send completed images to
their channels, delete local files, and mark jobs as sent in the database.
"""


async def delete_stored_images(bot):
    """
    Deliver completed jobs' images to channels and remove local files.

    The function iterates over completed jobs, attempts to send the image
    to the configured channel, deletes the file regardless of delivery
    success to prevent disk accumulation, and marks the job as sent.
    """
    completed_jobs = await bot.db.get_completed_jobs()

    for job in completed_jobs:
        job_id = job["job_id"]
        channel_id = job["channel_id"]
        file_path = job["output_path"]
        user_id = job["user_id"]
        model_type = job["model_type"]

        if not os.path.exists(file_path):
            print(f"⚠️ File missing for job #{job_id}: {file_path}")
            await bot.db.mark_job_sent(job_id)
            continue

        try:
            channel = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)
        except Exception:
            channel = None

        try:
            if channel:
                await channel.send(
                    content=f"Upscale complete for <@{user_id}>! (Mode: `{model_type}`)",
                    file=discord.File(file_path),
                )
                print(f"📨 Delivered job #{job_id}")

            os.remove(file_path)
            print(f"🗑️ Deleted local file: {file_path}")

            await bot.db.mark_job_sent(job_id)

        except discord.Forbidden:
            print(f"❌ No permission to send in channel {channel_id}")
            await bot.db.mark_job_sent(job_id)
            if os.path.exists(file_path):
                os.remove(file_path)

        except Exception as e:
            print(f"❌ Error delivering job #{job_id}: {e}")