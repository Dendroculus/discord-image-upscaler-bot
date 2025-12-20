import os
import asyncpg
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

DB_DSN = os.getenv("POSTGRE_CONN_STRING")


class Database:
    """
    Async PostgreSQL database handler for managing upscale job queues.

    Responsibilities:
    - Manage connection pooling with asyncpg
    - Initialize and migrate database schema
    - Handle job lifecycle (queued → processing → completed / failed / sent)
    - Provide atomic job-claiming for concurrent workers
    """

    def __init__(self, dsn: str = DB_DSN):
        """
        Initialize the Database instance.

        Args:
            dsn (str): PostgreSQL DSN connection string.
        """
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """
        Create an asyncpg connection pool.

        Must be called before any database operation.
        """
        self.pool = await asyncpg.create_pool(self.dsn)

    async def close(self):
        """
        Close the database connection pool gracefully.
        """
        if self.pool:
            await self.pool.close()

    async def init_schema(self):
        """
        Initialize and migrate the database schema.

        - Creates the `upscale_jobs` table if it does not exist
        - Ensures `channel_id`, `token`, and `application_id` columns exist
        - Backfills existing NULL `channel_id` values with 0
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS upscale_jobs (
                    job_id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    channel_id BIGINT NOT NULL,
                    image_url TEXT NOT NULL,
                    model_type TEXT NOT NULL,
                    token TEXT,
                    application_id TEXT,
                    status TEXT DEFAULT 'queued',
                    output_path TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                """
            )

            # Ensure schema consistency for older deployments
            await conn.execute(
                "ALTER TABLE upscale_jobs ADD COLUMN IF NOT EXISTS channel_id BIGINT;"
            )
            await conn.execute(
                "ALTER TABLE upscale_jobs ADD COLUMN IF NOT EXISTS token TEXT;"
            )
            await conn.execute(
                "ALTER TABLE upscale_jobs ADD COLUMN IF NOT EXISTS application_id TEXT;"
            )
            
            await conn.execute(
                "UPDATE upscale_jobs SET channel_id = 0 WHERE channel_id IS NULL;"
            )
            await conn.execute(
                "ALTER TABLE upscale_jobs ALTER COLUMN channel_id SET NOT NULL;"
            )

    async def add_job(
        self,
        user_id: int,
        channel_id: int,
        image_url: str,
        model_type: str,
        token: str,
        application_id: str
    ) -> int:
        """
        Insert a new upscale job into the queue.

        Args:
            user_id (int): Discord user ID who requested the job
            channel_id (int): Channel where the job originated
            image_url (str): Source image URL
            model_type (str): Upscaling model identifier
            token (str): Interaction token for updating the message
            application_id (str): Bot application ID

        Returns:
            int: Newly created job_id
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO upscale_jobs (user_id, channel_id, image_url, model_type, token, application_id)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING job_id
                """,
                user_id,
                channel_id,
                image_url,
                model_type,
                token,
                application_id
            )

    async def claim_next_queued_job(self) -> Optional[Dict[str, Any]]:
        """
        Atomically claim the oldest queued job for processing.

        Uses row-level locking with SKIP LOCKED to allow safe concurrent
        workers without double-processing jobs.

        Returns:
            Optional[Dict[str, Any]]:
                A dictionary containing job fields required for processing,
                or None if no queued job is available.
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    """
                    SELECT job_id, user_id, channel_id, image_url, model_type, token, application_id
                    FROM upscale_jobs
                    WHERE status = 'queued'
                    ORDER BY created_at ASC
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                    """
                )

                if row:
                    await conn.execute(
                        "UPDATE upscale_jobs SET status = 'processing' WHERE job_id = $1",
                        row["job_id"],
                    )
                    return dict(row)

                return None

    async def mark_processing(self, job_id: int):
        """
        Mark a job as currently being processed.

        Args:
            job_id (int): Job identifier
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE upscale_jobs SET status = 'processing' WHERE job_id = $1",
                job_id,
            )

    async def mark_completed(self, job_id: int, output_path: str):
        """
        Mark a job as completed and store its output path.

        Args:
            job_id (int): Job identifier
            output_path (str): Path or identifier of the generated output
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE upscale_jobs
                SET status = 'completed', output_path = $2
                WHERE job_id = $1
                """,
                job_id,
                output_path,
            )

    async def mark_failed(self, job_id: int, reason: str):
        """
        Mark a job as failed.

        The failure reason is stored in `output_path` for inspection/logging.

        Args:
            job_id (int): Job identifier
            reason (str): Failure reason or error message
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE upscale_jobs
                SET status = 'failed', output_path = $2
                WHERE job_id = $1
                """,
                job_id,
                reason,
            )

    async def get_completed_jobs(self):
        """
        Retrieve all completed jobs.

        Returns:
            list[dict]: List of completed job records
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT 
                    job_id, user_id, channel_id, image_url, 
                    model_type, status, output_path, created_at
                FROM upscale_jobs 
                WHERE status = 'completed'
                """
            )
            return [dict(r) for r in rows]
        
    async def mark_job_sent(self, job_id: int):
        """
        Mark a completed job as sent to the user.

        Args:
            job_id (int): Job identifier
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE upscale_jobs SET status = 'sent' WHERE job_id = $1",
                job_id,
            )

    async def get_queue_position(self) -> int:
        """
        Get the current number of jobs ahead in the queue.

        Counts jobs that are either queued or currently processing.

        Returns:
            int: Number of active jobs in the queue
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM upscale_jobs
                WHERE status IN ('queued', 'processing')
                """
            )