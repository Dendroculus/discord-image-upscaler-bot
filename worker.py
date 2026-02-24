"""
worker.py

Background worker process for processing image upscaling jobs.
Responsibility: Polls the database for queued jobs, manages the AI upscaling
lifecycle, uploads results, and notifies the Discord webhook.
"""
from utils.patch_fix import patch_torchvision
import asyncio
import aiohttp
import os
import glob
import logging
from functools import wraps
from typing import Optional, Dict, Any
from asyncio.proactor_events import _ProactorBasePipeTransport

import contextlib
from database import Database
from loggers.bot_logger import init_logging
from utils.image_processing import AIUpscaler
from constants.emojis import process, customs

from services.storage_service import StorageService
from services.notification_service import NotificationService

def silence_event_loop_closed(func):
    """
    Wrapper to suppress 'Event loop is closed' RuntimeError on Windows.
    
    Args:
        func (Callable): The function to wrap.
        
    Returns:
        Callable: The wrapped function.
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
        """
        Initializes the worker with configuration and dependencies.
        
        Args:
            poll_interval (float): Seconds to wait between database polls.
        """
        self.db = Database()
        self.poll_interval = poll_interval
        self.session: Optional[aiohttp.ClientSession] = None
        self.ai_engine = AIUpscaler()

    async def start(self):
        """
        Initializes the worker by setting up the database connection, performing startup maintenance tasks, and then entering the main processing loop to handle queued jobs.
        """
        async with aiohttp.ClientSession() as session:
            self.session = session
            
            await self.db.connect()
            await self.db.init_schema()
            
            logger.info("🧹 Running startup maintenance...")
            
            orphaned_files = glob.glob("temp_*.png")
            for f in orphaned_files:
                try:
                    os.remove(f)
                except OSError:
                    pass
            
            await self.db.recover_stale_jobs()
            await self.db.prune_old_jobs()
            
            logger.info("🛠️ Worker online. Waiting for queued jobs...")
            await self._run_loop()

    async def _run_loop(self):
        """
        Continuously polls the database for new queued jobs. When a job is claimed, it processes the job and then returns to polling. If no jobs are found, it waits for a specified interval before checking again.
        """
        while True:
            job = await self.db.claim_next_queued_job()
            if job:
                await self._process_job(job)
            else:
                await asyncio.sleep(self.poll_interval)

    async def _run_heartbeat_monitor(self, job_id: int):
        """
        Periodically updates the heartbeat timestamp for the given job ID in the database to indicate that the worker is still active and processing the job.
        
        Args:
            job_id (int): The ID of the active job.
        """
        while True:
            await asyncio.sleep(30)
            try:
                await self.db.update_heartbeat(job_id)
                logger.debug(f"💓 Job #{job_id} heartbeat sent.")
            except Exception as e:
                logger.warning(f"Heartbeat failed for #{job_id}: {e}")

    async def _update_discord_status(self, job: Dict[str, Any], status_text: str, color: int):
        """
        Adds or updates a status embed in the original Discord message to reflect the current processing stage.
        
        Args:
            job (Dict[str, Any]): The job dictionary containing necessary information for the Discord message.
            status_text (str): The text to display in the embed's "Status" field.
            color (int): The color code for the embed.
        """
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
        """
        Deletes the progress message in Discord for a given job.
        
        Args:
            job (Dict[str, Any]): The job dictionary.
        """
        if not (job.get("token") and job.get("application_id") and self.session):
            return

        url = f"https://discord.com/api/v10/webhooks/{job['application_id']}/{job['token']}/messages/@original"
        try:
            async with self.session.delete(url) as resp:
                await resp.read()
        except Exception as e:
            logger.warning(f"Failed to delete progress message: {e}")

    async def _process_job(self, job: Dict[str, Any]):
        """
        Handles the entire lifecycle of a single job, from processing the image to uploading it and sending the final notification.
        
        Args:
            job (Dict[str, Any]): The job data dictionary.
        """
        job_id = job["job_id"]
        logger.info(f"🔄 Processing job #{job_id} ({job['model_type']}) ...")

        heartbeat_task = asyncio.create_task(self._run_heartbeat_monitor(job_id))

        try:
            await self._update_discord_status(
                job, 
                f"{process['processing']} **Processing...**", 
                5763719
            )
            
            image_data = await self.ai_engine.run_upscale(
                job["image_url"],
                job["job_id"],
                job["model_type"],
                self.session
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
            logger.exception(f"❌ Job #{job_id} failed:")
            
        finally:
            heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat_task

async def main():
    """
    Main entry point for the worker script.
    """
    worker = Worker(poll_interval=2.0)
    await worker.start()

if __name__ == "__main__":
    asyncio.run(main())