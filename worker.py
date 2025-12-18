import os
from utils.PatchFix import patch_torchvision
import asyncio
from typing import Optional, Dict, Any
from database import Database
from utils.ImageProcessing import process_image
from utils.Deliverer import deliver_result

patch_torchvision()

"""
worker.py

Background worker that polls the database for queued upscaling jobs,
processes them with the AI pipeline, and updates job status transitions.

Logic flow:
1. On start(), connect to the database and ensure schema is present.
2. Enter an infinite loop that:
   - claims the next queued job (atomically),
   - if a job exists, process it; otherwise sleep for poll_interval seconds.
3. For each claimed job:
   - run the image processing in a thread (using asyncio.to_thread) to avoid
     blocking the event loop,
   - mark the job as completed with output path on success,
   - mark the job as failed with an error message on exception.
"""

class Worker:
    """
    Worker that continually claims and processes jobs.

    Attributes:
        db (Database): Database helper used to claim and update jobs.
        poll_interval (float): Pause duration when no job is available.
    """

    def __init__(self, poll_interval: float = 2.0):
        """
        Initialize the worker.

        Args:
            poll_interval: Seconds to wait between polling attempts when no job is found.
        """
        self.db = Database()
        self.poll_interval = poll_interval

    async def start(self):
        """
        Connect and initialize the database, then start the processing loop.

        Steps:
        1. Connect to DB and initialize schema.
        2. Log that the worker is online.
        3. Enter the polling loop.
        """
        await self.db.connect()
        await self.db.init_schema()
        print("🛠️ Worker online. Waiting for queued jobs...")
        await self._run_loop()

    async def _run_loop(self):
        """
        Poll for jobs indefinitely.

        Behavior:
        - Attempt to claim the next queued job.
        - If a job is returned, process it.
        - If not, sleep for self.poll_interval seconds, then retry.
        """
        while True:
            job = await self._next_job()
            if job:
                await self._process_job(job)
            else:
                await asyncio.sleep(self.poll_interval)

    async def _next_job(self) -> Optional[Dict[str, Any]]:
        """
        Claim the next queued job using an atomic DB operation.

        Returns:
            A job dict if available, otherwise None.
        """
        return await self.db.claim_next_queued_job()

    async def _process_job(self, job: Dict[str, Any]):
        job_id = job["job_id"]
        print(f"🔄 Processing job #{job_id} ({job['model_type']}) ...")
        
        output_path = None 
        try:
            output_path = await asyncio.to_thread(
                process_image,
                job["image_url"],
                job["job_id"],
                job["model_type"],
            )

            if output_path:
                success = await deliver_result(
                    channel_id=job["channel_id"],
                    file_path=output_path,
                    user_id=job["user_id"],
                    model_type=job["model_type"]
                )
                
                if success:
                    await self.db.mark_completed(job_id, "Uploaded to Discord")
                    await self.db.mark_job_sent(job_id)
                    print(f"✅ Job #{job_id} completed and delivered.")
                else:
                    raise RuntimeError("Discord upload failed.")
            else:
                raise RuntimeError("AI engine returned no output.")

        except Exception as e:
            await self.db.mark_failed(job_id, str(e))
            print(f"❌ Job #{job_id} failed: {e}")

        finally:
            if output_path and os.path.exists(output_path):
                try:
                    os.remove(output_path)
                    print(f"🗑️ Cleaned up temp file: {output_path}")
                except Exception as cleanup_err:
                    print(f"⚠️ Cleanup error: {cleanup_err}")


async def main():
    """
    Async entrypoint to run the worker standalone.

    Usage:
        asyncio.run(main())
    """
    worker = Worker(poll_interval=2.0)
    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())