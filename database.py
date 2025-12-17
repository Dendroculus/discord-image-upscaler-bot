import os
import asyncpg
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

DB_DSN = os.getenv("POSTGRE_CONN_STRING")

"""
database.py

Asynchronous thin wrapper around asyncpg to manage upscale job persistence.

The Database class offers connection pool management, schema initialization,
simple in-place migrations, and CRUD-like helpers used by the bot and worker.
"""


class Database:
    """
    Async helper for storing and retrieving upscale jobs.

    The class encapsulates an asyncpg connection pool and provides methods to
    initialize schema, add jobs, claim jobs for processing, and update status
    transitions.
    """

    def __init__(self, dsn: str = DB_DSN):
        """
        Initialize the Database helper.

        Args:
            dsn: The PostgreSQL DSN used to create the connection pool.
        """
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """
        Create the asyncpg connection pool.

        This must be awaited before performing queries.
        """
        self.pool = await asyncpg.create_pool(self.dsn)

    async def close(self):
        """
        Close the connection pool if it exists.
        """
        if self.pool:
            await self.pool.close()

    async def init_schema(self):
        """
        Ensure the 'upscale_jobs' table exists and perform lightweight migrations.

        The table stores job metadata and supports a simple status lifecycle:
        'queued' -> 'processing' -> 'completed' -> 'sent' (or 'failed').
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
                    status TEXT DEFAULT 'queued',
                    output_path TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                """
            )
            await conn.execute("ALTER TABLE upscale_jobs ADD COLUMN IF NOT EXISTS channel_id BIGINT;")
            await conn.execute("UPDATE upscale_jobs SET channel_id = 0 WHERE channel_id IS NULL;")
            await conn.execute("ALTER TABLE upscale_jobs ALTER COLUMN channel_id SET NOT NULL;")

    async def add_job(self, user_id: int, channel_id: int, image_url: str, model_type: str) -> int:
        """
        Insert a new upscale job and return its generated job_id.
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO upscale_jobs (user_id, channel_id, image_url, model_type)
                VALUES ($1, $2, $3, $4)
                RETURNING job_id
                """,
                user_id,
                channel_id,
                image_url,
                model_type,
            )

    async def claim_next_queued_job(self) -> Optional[Dict[str, Any]]:
        """
        Atomically claim the oldest queued job using row locking to support
        multiple workers safely. Uses FOR UPDATE SKIP LOCKED to prevent
        double-claiming.
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    """
                    SELECT * FROM upscale_jobs
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
        Transition a job to the 'processing' status.
        """
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE upscale_jobs SET status = 'processing' WHERE job_id = $1", job_id)

    async def mark_completed(self, job_id: int, output_path: str):
        """
        Mark a job as completed and record the path to the generated output file.
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE upscale_jobs SET status = 'completed', output_path = $2 WHERE job_id = $1",
                job_id,
                output_path,
            )

    async def mark_failed(self, job_id: int, reason: str):
        """
        Mark a job as failed. The failure reason is stored in the output_path
        column for operational visibility.
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE upscale_jobs SET status = 'failed', output_path = $2 WHERE job_id = $1",
                job_id,
                reason,
            )

    async def get_completed_jobs(self):
        """
        Fetch all jobs with status 'completed' that are ready for delivery.
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM upscale_jobs WHERE status = 'completed'")
            return [dict(r) for r in rows]

    async def mark_job_sent(self, job_id: int):
        """
        Mark a job as 'sent' after delivery to avoid duplicate deliveries.
        """
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE upscale_jobs SET status = 'sent' WHERE job_id = $1", job_id)