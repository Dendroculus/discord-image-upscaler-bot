import os
import discord

async def delete_stored_images(bot):
    """
    Fetches completed jobs from the DB, sends the image to the user, 
    and then deletes the local file to save space.
    """
    # Access the database attached to the bot instance
    completed_jobs = await bot.db.get_completed_jobs()
    
    for job in completed_jobs:
        job_id = job["job_id"]
        channel_id = job["channel_id"]
        file_path = job["output_path"]
        user_id = job["user_id"]
        model_type = job["model_type"]

        # 1. Validate File Exists
        if not os.path.exists(file_path):
            print(f"⚠️ File missing for job #{job_id}: {file_path}")
            await bot.db.mark_job_sent(job_id)
            continue

        # 2. Get the Channel
        try:
            # Try cache first, then API
            channel = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)
        except Exception:
            channel = None

        # 3. Send & Delete
        try:
            if channel:
                await channel.send(
                    content=f"Upscale complete for <@{user_id}>! (Mode: `{model_type}`)",
                    file=discord.File(file_path)
                )
                print(f"📨 Delivered job #{job_id}")

            # ✅ CRITICAL: Delete file immediately after sending
            os.remove(file_path)
            print(f"🗑️ Deleted local file: {file_path}")

            # Mark as sent in DB
            await bot.db.mark_job_sent(job_id)

        except discord.Forbidden:
            print(f"❌ No permission to send in channel {channel_id}")
            await bot.db.mark_job_sent(job_id)
            # Still delete the file so it doesn't rot on your drive
            if os.path.exists(file_path): 
                os.remove(file_path)
        
        except Exception as e:
            print(f"❌ Error delivering job #{job_id}: {e}")