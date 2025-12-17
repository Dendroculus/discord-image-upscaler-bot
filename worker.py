from utils.PatchFix import patch_torchvision
import asyncio
from typing import Optional, Dict, Any
from database import Database
from utils.ImageProcessing import process_image  


patch_torchvision()

class Worker:
    """
    Dedicated worker that continuously consumes queued jobs and runs the
    AI upscaling pipeline.
    """

    def __init__(self, poll_interval: float = 2.0):
        self.db = Database()
        self.poll_interval = poll_interval

    async def start(self):
        """Connect to the database and start the processing loop."""
        await self.db.connect()
        await self.db.init_schema()
        print("🛠️ Worker online. Waiting for queued jobs...")
        await self._run_loop()

    async def _run_loop(self):
        """Main producer-consumer loop."""
        while True:
            job = await self._next_job()
            if job:
                await self._process_job(job)
            else:
                await asyncio.sleep(self.poll_interval)

    async def _next_job(self) -> Optional[Dict[str, Any]]:
        """Fetch the next queued job and mark it as processing."""
        job = await self.db.get_next_queued_job()
        if job:
            await self.db.mark_processing(job["job_id"])
        return job

    async def _process_job(self, job: Dict[str, Any]):
        """Run the AI engine for a single job."""
        job_id = job["job_id"]
        print(f"🔄 Processing job #{job_id} ({job['model_type']}) ...")
        try:
            output_path = await asyncio.to_thread(
                process_image, 
                job["image_url"],
                job["job_id"],     
                job["model_type"]  
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
    """Entry point to run the worker process."""
    worker = Worker(poll_interval=2.0)
    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())