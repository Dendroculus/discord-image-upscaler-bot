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
    """
    Wrapper to suppress 'Event loop is closed' RuntimeError on Windows.
    
    This is required because the ProactorEventLoop on Windows can raise 
    noisy exceptions during the shutdown of async generators or transports.
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

    This class handles database polling, job claiming, resource management,
    heartbeat monitoring, and the coordination of the image processing pipeline.

    Attributes:
        db (Database): The database interface for job queue management.
        poll_interval (float): Time in seconds to wait when the queue is empty.
        session (Optional[aiohttp.ClientSession]): Persistent HTTP session for API requests.
    """

    def __init__(self, poll_interval: float = 2.0):
        """
        Initializes the Worker instance.

        Args:
            poll_interval (float): The sleep duration between queue checks when idle.
        """
        self.db = Database()
        self.poll_interval = poll_interval
        self.session: Optional[aiohttp.ClientSession] = None

    async def start(self):
        """
        Bootstraps the worker service.

        Establishes the HTTP session and database connection, performs startup
        maintenance (recovering stale jobs and pruning logs), and initiates
        the main processing loop.
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
        Executes the continuous job polling loop.

        This method checks the database for queued jobs. If a job is found,
        it is processed immediately. If the queue is empty, the worker sleeps
        for `poll_interval` seconds to reduce database load.
        """
        while True:
            job = await self.db.claim_next_queued_job()
            if job:
                await self._process_job(job)
            else:
                await asyncio.sleep(self.poll_interval)

    async def _run_heartbeat_monitor(self, job_id: int):
        """
        Background task that updates the job's heartbeat timestamp.

        This prevents the database recovery logic from marking the job as stale
        during long-running processes.

        Args:
            job_id (int): The unique identifier of the job to monitor.
        """
        try:
            while True:
                await asyncio.sleep(30)
                try:
                    await self.db.update_heartbeat(job_id)
                    logger.debug(f"💓 Job #{job_id} heartbeat sent.")
                except Exception as e:
                    logger.warning(f"Heartbeat failed for #{job_id}: {e}")
        except asyncio.CancelledError:
            pass

    async def _update_discord_status(self, job: Dict[str, Any], status_text: str, color: int):
        """
        Updates the Discord interaction message with the current job status.

        Args:
            job (Dict[str, Any]): The job dictionary containing tokens and IDs.
            status_text (str): The status message to display in the embed.
            color (int): The hex color code for the embed border.
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
        Deletes the original interaction response (progress bar) upon completion.

        Args:
            job (Dict[str, Any]): The job dictionary containing tokens and IDs.
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
        Orchestrates the end-to-end processing pipeline for a single job.

        Sequence:
        1. Starts the heartbeat monitor.
        2. Updates Discord status to 'Processing'.
        3. Offloads the heavy AI processing to a separate thread.
        4. Updates Discord status to 'Uploading'.
        5. Uploads the result to Azure and delivers the final link to Discord.
        6. Marks the job as completed in the database and cleans up UI elements.

        Args:
            job (Dict[str, Any]): The job payload from the database.
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

            success = await deliver_result(
                session=self.session,
                channel_id=job["channel_id"],
                image_data=image_data, 
                user_id=job["user_id"],
                model_type=job["model_type"]
            )
            
            if not success:
                raise RuntimeError("Discord delivery failed.")

            await self.db.mark_completed(job_id, "Uploaded to Azure")
            await self.db.mark_job_sent(job_id)
            await self._cleanup_discord_message(job)

            logger.info(f"Job #{job_id} completed and delivered.")

        except Exception as e:
            await self.db.mark_failed(job_id, str(e))
            logger.error(f"❌ Job #{job_id} failed: {e}")
            
        finally:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

async def main():
    worker = Worker(poll_interval=2.0)
    await worker.start()

if __name__ == "__main__":
    asyncio.run(main())