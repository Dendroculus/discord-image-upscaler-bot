from utils.PatchFix import patch_torchvision
import asyncio
from typing import Optional, Dict, Any
from database import Database
from utils.ImageProcessing import process_image
from utils.Deliverer import deliver_result

patch_torchvision()

"""
worker.py
Background worker that polls for jobs, processes them in memory, and uploads to Azure.
"""

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
        print(f"🔄 Processing job #{job_id} ({job['model_type']}) ...")
        
        try:
            image_data = await asyncio.to_thread(
                process_image,
                job["image_url"],
                job["job_id"],
                job["model_type"],
            )

            if image_data:
                success = await deliver_result(
                    channel_id=job["channel_id"],
                    image_data=image_data, 
                    user_id=job["user_id"],
                    model_type=job["model_type"]
                )
                
                if success:
                    await self.db.mark_completed(job_id, "Uploaded to Azure")
                    await self.db.mark_job_sent(job_id)
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