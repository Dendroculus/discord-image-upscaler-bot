import os
import asyncpg
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

DB_DSN = os.getenv("POSTGRE_CONN_STRING")


class Database:
    """
    Thin async wrapper around asyncpg for storing and retrieving upscale jobs.
    Handles schema initialization and simple in-place migrations.
    """

    def __init__(self, dsn: str = DB_DSN):
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Initialize the connection pool."""
        self.pool = await asyncpg.create_pool(self.dsn)

    async def close(self):
        """Close the connection pool."""
        if self.pool:
            await self.pool.close()

    async def init_schema(self):
        """
        Create or migrate the upscale_jobs table.
        Ensures channel_id exists and is NOT NULL for routing deliveries.
        """
        async with self.pool.acquire() as conn:
            # Base table
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
            # Migration: add channel_id if missing
            await conn.execute("ALTER TABLE upscale_jobs ADD COLUMN IF NOT EXISTS channel_id BIGINT;")
            await conn.execute("UPDATE upscale_jobs SET channel_id = 0 WHERE channel_id IS NULL;")
            await conn.execute("ALTER TABLE upscale_jobs ALTER COLUMN channel_id SET NOT NULL;")

    async def add_job(self, user_id: int, channel_id: int, image_url: str, model_type: str) -> int:
        """Insert a new job and return its ID."""
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

    async def get_next_queued_job(self) -> Optional[Dict[str, Any]]:
        """Fetch the oldest queued job. Returns None if no job is available."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM upscale_jobs
                WHERE status = 'queued'
                ORDER BY created_at ASC
                LIMIT 1
                """
            )
            return dict(row) if row else None

    async def mark_processing(self, job_id: int):
        """Mark a job as processing."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE upscale_jobs SET status = 'processing' WHERE job_id = $1",
                job_id,
            )

    async def mark_completed(self, job_id: int, output_path: str):
        """Mark a job as completed and store the output path."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE upscale_jobs SET status = 'completed', output_path = $2 WHERE job_id = $1",
                job_id,
                output_path,
            )

    async def mark_failed(self, job_id: int, reason: str):
        """Mark a job as failed (reason is logged server-side only)."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE upscale_jobs SET status = 'failed', output_path = $2 WHERE job_id = $1",
                job_id,
                reason,
            )

    async def get_completed_jobs(self):
        """Return all jobs ready to be delivered (completed but not sent)."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM upscale_jobs WHERE status = 'completed'")
            return [dict(r) for r in rows]

    async def mark_job_sent(self, job_id: int):
        """Mark a job as sent to avoid duplicate deliveries."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE upscale_jobs SET status = 'sent' WHERE job_id = $1",
                job_id,
            )