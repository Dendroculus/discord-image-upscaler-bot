from utils.PatchFix import patch_torchvision
import asyncio
from typing import Optional, Dict, Any
from database import Database
from utils.ImageProcessing import process_image

patch_torchvision()

"""
worker.py

Background worker process that continuously claims queued jobs from the
database, runs the AI upscaling pipeline, and updates job status transitions.
Instantiate Worker and call `start()` to run the processing loop.
"""


class Worker:
    """
    Worker that polls the database for queued jobs, processes them, and
    updates their status based on the processing outcome.

    Attributes:
        db (Database): Database helper instance.
        poll_interval (float): Seconds to wait between polls when no job is found.
    """

    def __init__(self, poll_interval: float = 2.0):
        """
        Initialize the worker and its database connection helper.

        Args:
            poll_interval: Interval in seconds between polling attempts.
        """
        self.db = Database()
        self.poll_interval = poll_interval

    async def start(self):
        """
        Connect to the database, initialize schema, and start the processing loop.
        """
        await self.db.connect()
        await self.db.init_schema()
        print("🛠️ Worker online. Waiting for queued jobs...")
        await self._run_loop()

    async def _run_loop(self):
        """
        Forever loop that fetches the next job and processes it. Sleeps for the
        configured poll interval when no job is available.
        """
        while True:
            job = await self._next_job()
            if job:
                await self._process_job(job)
            else:
                await asyncio.sleep(self.poll_interval)

    async def _next_job(self) -> Optional[Dict[str, Any]]:
        """
        Atomically claim the next queued job, safe for multiple worker instances.
        """
        return await self.db.claim_next_queued_job()

    async def _process_job(self, job: Dict[str, Any]):
        """
        Execute the AI upscaling pipeline for a single job and update status.

        The actual CPU/GPU-bound processing is delegated to `process_image`
        and executed in a thread pool via asyncio.to_thread.

        Args:
            job: Job dictionary containing keys like job_id, image_url, and model_type.
        """
        job_id = job["job_id"]
        print(f"🔄 Processing job #{job_id} ({job['model_type']}) ...")
        try:
            output_path = await asyncio.to_thread(
                process_image,
                job["image_url"],
                job["job_id"],
                job["model_type"],
            )

            if output_path:
                await self.db.mark_completed(job_id, output_path)
                print(f"Job #{job_id} completed -> {output_path}")
            else:
                raise RuntimeError("AI engine returned no output.")
        except Exception as e:
            await self.db.mark_failed(job_id, str(e))
            print(f"❌ Job #{job_id} failed: {e}")


async def main():
    """
    Async entrypoint for running the worker process standalone.
    """
    worker = Worker(poll_interval=2.0)
    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())