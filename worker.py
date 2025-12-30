from utils.PatchFix import patch_torchvision
import asyncio
import aiohttp
import os
import logging
from functools import wraps
from typing import Optional, Dict, Any
from asyncio.proactor_events import _ProactorBasePipeTransport

import contextlib
from database import Database
from loggers.BotLogger import init_logging
from utils.ImageProcessing import process_image
from constants.Emojis import process, customs

from utils.StorageService import StorageService
from utils.NotificationService import NotificationService

def silence_event_loop_closed(func):
    """
    Wrapper to suppress 'Event loop is closed' RuntimeError on Windows.
    """
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

class Worker:
    """
    Orchestrates the lifecycle of background image upscaling jobs.
    Now acts as a Coordinator between the DB, AI Engine, Storage, and Notifier.
    """

    def __init__(self, poll_interval: float = 2.0):
        self.db = Database()
        self.poll_interval = poll_interval
        self.session: Optional[aiohttp.ClientSession] = None

    async def start(self):
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
        while True:
            job = await self.db.claim_next_queued_job()
            if job:
                await self._process_job(job)
            else:
                await asyncio.sleep(self.poll_interval)

    async def _run_heartbeat_monitor(self, job_id: int):
        while True:
            await asyncio.sleep(30)
            try:
                await self.db.update_heartbeat(job_id)
                logger.debug(f"💓 Job #{job_id} heartbeat sent.")
            except Exception as e:
                logger.warning(f"Heartbeat failed for #{job_id}: {e}")

    async def _update_discord_status(self, job: Dict[str, Any], status_text: str, color: int):
        if not (job.get("token") and job.get("application_id") and self.session):
            return

        url = f"https://discord.com/api/v10/webhooks/{job['application_id']}/{job['token']}/messages/@original"
        embed = {
            "title": f"{customs['paint']} Image Upscaler",
            "description": "Your image is being enhanced.",
            "color": color, 
            "fields": [{"name": "Status", "value": status_text, "inline": True}],
            "footer": {"text": "This might take a moment..."}
        }
        
        try:
            async with self.session.patch(url, json={"embeds": [embed]}) as response:
                await response.read()
        except Exception as e:
            logger.warning(f"Failed to update status embed: {e}")

    async def _cleanup_discord_message(self, job: Dict[str, Any]):
        if not (job.get("token") and job.get("application_id") and self.session):
            return

        url = f"https://discord.com/api/v10/webhooks/{job['application_id']}/{job['token']}/messages/@original"
        try:
            async with self.session.delete(url) as resp:
                await resp.read()
        except Exception as e:
            logger.warning(f"Failed to delete progress message: {e}")

    async def _process_job(self, job: Dict[str, Any]):
        job_id = job["job_id"]
        logger.info(f"🔄 Processing job #{job_id} ({job['model_type']}) ...")

        heartbeat_task = asyncio.create_task(self._run_heartbeat_monitor(job_id))

        try:
            await self._update_discord_status(
                job, 
                f"{process['processing']} **Processing...**", 
                5763719
            )
            
            image_data = await asyncio.to_thread(
                process_image,
                job["image_url"],
                job["job_id"],
                job["model_type"],
            )

            if not image_data:
                raise RuntimeError("AI engine returned no output.")

            await self._update_discord_status(
                job,
                f"{process['uploading']} **Uploading...**", 
                5793266
            )

            file_url = await StorageService.upload_file(image_data)
            
            await NotificationService.send_delivery_message(
                session=self.session,
                channel_id=job["channel_id"],
                user_id=job["user_id"],
                model_type=job["model_type"],
                file_url=file_url
            )
            
            await self.db.mark_completed(job_id, "Uploaded to Azure")
            await self.db.mark_job_sent(job_id)
            await self._cleanup_discord_message(job)

            logger.info(f"Job #{job_id} completed and delivered.")

        except Exception as e:
            await self.db.mark_failed(job_id, str(e))
            logger.error(f"❌ Job #{job_id} failed: {e}")
            
        finally:
            heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat_task

async def main():
    worker = Worker(poll_interval=2.0)
    await worker.start()

if __name__ == "__main__":
    asyncio.run(main())