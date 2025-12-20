from utils.PatchFix import patch_torchvision
import asyncio
import aiohttp
from typing import Optional, Dict, Any
from database import Database
from utils.ImageProcessing import process_image
from utils.Deliverer import deliver_result
from constants.Emojis import process, customs

patch_torchvision()

"""
worker.py
Background worker that polls for jobs, processes them in memory, and uploads to Azure.
"""

async def update_status_embed(application_id: str, token: str, status: str, color: int):
    """
    Updates the existing Embed with a new status and color.
    """
    url = f"https://discord.com/api/v10/webhooks/{application_id}/{token}/messages/@original"
    
    embed = {
        "title": f"{customs['paint']} Image Upscaler",
        "description": "Your image is being enhanced.",
        "color": color, 
        "fields": [
            {"name": "Status", "value": status, "inline": True},
        ],
        "footer": {"text": "This might take a moment..."}
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            await session.patch(url, json={"embeds": [embed]})
    except Exception as e:
        print(f"Failed to update status embed: {e}")

async def delete_progress_message(application_id: str, token: str):
    """
    Deletes the progress message to clean up the chat.
    """
    url = f"https://discord.com/api/v10/webhooks/{application_id}/{token}/messages/@original"
    try:
        async with aiohttp.ClientSession() as session:
            await session.delete(url)
    except Exception as e:
        print(f"Failed to delete progress message: {e}")

class Worker:
    def __init__(self, poll_interval: float = 2.0):
        self.db = Database()
        self.poll_interval = poll_interval

    async def start(self):
        await self.db.connect()
        await self.db.init_schema()
        print("🛠️ Worker online. Waiting for queued jobs...")
        await self._run_loop()

    async def _run_loop(self):
        while True:
            job = await self._next_job()
            if job:
                await self._process_job(job)
            else:
                await asyncio.sleep(self.poll_interval)

    async def _next_job(self) -> Optional[Dict[str, Any]]:
        return await self.db.claim_next_queued_job()

    async def _process_job(self, job: Dict[str, Any]):
        job_id = job["job_id"]
        

        if job.get("token") and job.get("application_id"):
            # Update to BLUE: Processing
            await update_status_embed(
                job["application_id"], 
                job["token"], 
                f"{process['processing']} **Processing...**", 
                5763719
            )

        print(f"🔄 Processing job #{job_id} ({job['model_type']}) ...")
        
        try:
            image_data = await asyncio.to_thread(
                process_image,
                job["image_url"],
                job["job_id"],
                job["model_type"],
            )

            if image_data:
                if job.get("token") and job.get("application_id"):
                    await update_status_embed(
                        job["application_id"], 
                        job["token"], 
                        f"{process['uploading']} **Uploading...**", 
                        5793266
                    )

                success = await deliver_result(
                    channel_id=job["channel_id"],
                    image_data=image_data, 
                    user_id=job["user_id"],
                    model_type=job["model_type"]
                )
                
                if success:
                    await self.db.mark_completed(job_id, "Uploaded to Azure")
                    await self.db.mark_job_sent(job_id)

                    # --- CLEANUP: DELETE THE PROGRESS BAR ---
                    if job.get("token") and job.get("application_id"):
                         await delete_progress_message(job["application_id"], job["token"])

                    print(f"Job #{job_id} completed and delivered.")
                else:
                    raise RuntimeError("Discord delivery failed.")
            else:
                raise RuntimeError("AI engine returned no output.")

        except Exception as e:
            await self.db.mark_failed(job_id, str(e))
            print(f"❌ Job #{job_id} failed: {e}")


async def main():
    worker = Worker(poll_interval=2.0)
    await worker.start()

if __name__ == "__main__":
    asyncio.run(main())