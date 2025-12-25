from utils.PatchFix import patch_torchvision
import asyncio
import aiohttp
import os
import logging
from functools import wraps
from typing import Optional, Dict, Any
from asyncio.proactor_events import _ProactorBasePipeTransport

from database import Database
from loggers.BotLogger import init_logging
from utils.ImageProcessing import process_image
from utils.Deliverer import deliver_result
from constants.Emojis import process, customs

def silence_event_loop_closed(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except RuntimeError as e:
            if str(e) != 'Event loop is closed':
                raise
    return wrapper

_ProactorBasePipeTransport.__del__ = silence_event_loop_closed(_ProactorBasePipeTransport.__del__)

patch_torchvision()
init_logging(
    log_dir=os.path.join("logs", "worker_logs"), 
    log_file="worker.log"
)

logger = logging.getLogger("Worker")

"""
worker.py

Background worker service for the AI Upscaler application.
Responsible for polling the database for queued jobs, processing images using
the AI engine, and handling the delivery of results to Azure and Discord.
"""

async def update_status_embed(session: aiohttp.ClientSession, application_id: str, token: str, status: str, color: int):
    """
    Updates the Discord interaction embed with a new status message and color.
    Uses the shared aiohttp session to prevent connection overhead.
    """
    if session is None:
        return

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
        async with session.patch(url, json={"embeds": [embed]}) as response:
            await response.read()
    except Exception as e:
        logger.warning(f"Failed to update status embed: {e}")

async def delete_progress_message(session: aiohttp.ClientSession, application_id: str, token: str):
    """
    Deletes the original interaction response (progress bar) to clean up the channel
    after job completion. Safe to call even if session is closing.
    """
    if session is None:
        logger.warning("⚠️ Session was None when trying to delete message. Skipping.")
        return

    url = f"https://discord.com/api/v10/webhooks/{application_id}/{token}/messages/@original"
    try:
        async with session.delete(url) as resp:
            await resp.read()
    except Exception as e:
        logger.warning(f"Failed to delete progress message: {e}")

class Worker:
    """
    Main worker class responsible for job orchestration.
    
    Attributes:
        poll_interval (float): Time in seconds to wait between polling the database.
        db (Database): Database instance for job queue management.
        session (aiohttp.ClientSession): Shared HTTP session for API requests.
    """

    def __init__(self, poll_interval: float = 2.0):
        self.db = Database()
        self.poll_interval = poll_interval
        self.session: Optional[aiohttp.ClientSession] = None

    async def start(self):
        """
        Initializes the database connection, performs startup maintenance,
        and starts the main processing loop within a session context manager.
        """
        async with aiohttp.ClientSession() as session:
            self.session = session
            
            await self.db.connect()
            await self.db.init_schema()
            
            logger.info("🧹 Running startup maintenance...")
            await self.db.recover_stale_jobs()
            await self.db.prune_old_jobs()
            
            logger.info("🛠️ Worker online. Waiting for queued jobs...")
            await self._run_loop()

    async def _run_loop(self):
        """
        Continuous loop that checks for new jobs and processes them.
        """
        while True:
            job = await self._next_job()
            if job:
                await self._process_job(job)
            else:
                await asyncio.sleep(self.poll_interval)

    async def _next_job(self) -> Optional[Dict[str, Any]]:
        """
        Claims the next available 'queued' job from the database.
        """
        return await self.db.claim_next_queued_job()

    async def _process_job(self, job: Dict[str, Any]):
        """
        Executes the upscaling pipeline for a single job.
        
        Flow:
        1. Update status to 'Processing' (Blue).
        2. Upscale image via AI engine (blocking operation run in thread).
        3. Update status to 'Uploading' (Purple).
        4. Upload to Azure & Send Discord Message.
        5. Mark as Completed & Delete Progress Bar.
        """
        job_id = job["job_id"]
        
        if job.get("token") and job.get("application_id"):
            await update_status_embed(
                self.session,
                job["application_id"], 
                job["token"], 
                f"{process['processing']} **Processing...**", 
                5763719
            )

        logger.info(f"🔄 Processing job #{job_id} ({job['model_type']}) ...")
        
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
                        self.session,
                        job["application_id"], 
                        job["token"], 
                        f"{process['uploading']} **Uploading...**", 
                        5793266
                    )

                success = await deliver_result(
                    session=self.session,
                    channel_id=job["channel_id"],
                    image_data=image_data, 
                    user_id=job["user_id"],
                    model_type=job["model_type"]
                )
                
                if success:
                    await self.db.mark_completed(job_id, "Uploaded to Azure")
                    await self.db.mark_job_sent(job_id)

                    if job.get("token") and job.get("application_id"):
                         await delete_progress_message(
                             self.session,
                             job["application_id"], 
                             job["token"]
                         )

                    logger.info(f"Job #{job_id} completed and delivered.")
                else:
                    raise RuntimeError("Discord delivery failed.")
            else:
                raise RuntimeError("AI engine returned no output.")

        except Exception as e:
            await self.db.mark_failed(job_id, str(e))
            logger.error(f"❌ Job #{job_id} failed: {e}")


async def main():
    worker = Worker(poll_interval=2.0)
    await worker.start()

if __name__ == "__main__":
    asyncio.run(main())