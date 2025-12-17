import sys
import types
import torchvision

# Manually create the missing module to prevent the crash
if not hasattr(torchvision.transforms, 'functional_tensor'):
    from torchvision.transforms import functional as functional_new
    module = types.ModuleType("torchvision.transforms.functional_tensor")
    module.rgb_to_grayscale = functional_new.rgb_to_grayscale
    sys.modules["torchvision.transforms.functional_tensor"] = module

import discord
import os
import asyncio
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv
import database
from utils.image_processing import process_image

load_dotenv()

class UpscaleBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=None, intents=discord.Intents.default())
        self.pool = None

    async def setup_hook(self):
        # 1. Connect to DB
        self.pool = await database.get_db_pool()
        await database.init_db(self.pool)
        
        # 2. Sync Slash Commands
        await self.tree.sync()
        
        # 3. Start Background Tasks
        self.check_completed_jobs.start() # Delivery Task
        self.process_queued_jobs.start()  # Worker Task (New!)
        
        print("✅ All-in-One Bot Started! (Bot + Worker running)")

    async def close(self):
        await self.pool.close()
        await super().close()

    # --- TASK 1: The Worker (Processes the AI) ---
    @tasks.loop(seconds=2)
    async def process_queued_jobs(self):
        if self.pool is None: return

        async with self.pool.acquire() as conn:
            # Fetch oldest queued job
            job = await conn.fetchrow("SELECT * FROM upscale_jobs WHERE status = 'queued' ORDER BY created_at ASC LIMIT 1")

            if job:
                job_id = job['job_id']
                print(f"🔄 Processing Job #{job_id}...")
                
                await conn.execute("UPDATE upscale_jobs SET status = 'processing' WHERE job_id = $1", job_id)

                try:
                    # CRITICAL: We run this in a thread so the bot doesn't freeze!
                    # "to_thread" moves the heavy CPU/GPU work off the main loop.
                    output_path = await asyncio.to_thread(process_image, job['image_url'], job['model_type'])

                    if output_path:
                        print(f"✅ Job #{job_id} Processing Complete.")
                        await conn.execute(
                            "UPDATE upscale_jobs SET status = 'completed', output_path = $2 WHERE job_id = $1", 
                            job_id, output_path
                        )
                    else:
                        raise Exception("AI Engine returned None")
                
                except Exception as e:
                    print(f"❌ Job #{job_id} Failed: {e}")
                    await conn.execute("UPDATE upscale_jobs SET status = 'failed' WHERE job_id = $1", job_id)

    # --- TASK 2: The Postman (Delivers the Result) ---
    @tasks.loop(seconds=5)
    async def check_completed_jobs(self):
        if self.pool is None: return

        # Get finished jobs that haven't been sent yet
        # (We filter by status='completed', we assume 'sent' is a different status we set below)
        completed_jobs = await database.get_completed_jobs(self.pool)

        for job in completed_jobs:
            job_id = job['job_id']
            user_id = job['user_id']
            file_path = job['output_path']

            try:
                if not os.path.exists(file_path):
                    print(f"⚠️ File missing: {file_path}")
                    await database.mark_job_sent(self.pool, job_id)
                    continue

                user = await self.fetch_user(user_id) 
                
                await user.send(
                    content=f"**Upscale Ready!** (Job #{job_id})\nMode: `{job['model_type']}`",
                    file=discord.File(file_path)
                )
                print(f"📨 Delivered Job #{job_id} to User")

                await database.mark_job_sent(self.pool, job_id)

            except discord.Forbidden:
                print(f"❌ DMs closed for User {user_id}")
                await database.mark_job_sent(self.pool, job_id)
            except Exception as e:
                print(f"❌ Delivery Error: {e}")

    @check_completed_jobs.before_loop
    @process_queued_jobs.before_loop
    async def before_checks(self):
        await self.wait_until_ready()

bot = UpscaleBot()

@bot.tree.command(name="upscale", description="Upscale an image")
@app_commands.describe(image="Image to upscale", type="AI Model")
@app_commands.choices(type=[
    app_commands.Choice(name="General Photo", value="general"),
    app_commands.Choice(name="Anime / Illustration", value="anime")
])
async def upscale(interaction: discord.Interaction, image: discord.Attachment, type: app_commands.Choice[str]):
    if not image.content_type.startswith("image/"):
        return await interaction.response.send_message("❌ Image files only.", ephemeral=True)

    await interaction.response.defer(thinking=True)
    
    # Save to DB
    job_id = await database.add_job(bot.pool, interaction.user.id, image.url, type.value)

    await interaction.followup.send(f"**Job #{job_id} Queued!**\nI'll DM you when it's done.")

bot.run(os.getenv("DISCORD_TOKEN"))