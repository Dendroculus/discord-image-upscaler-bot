import asyncpg
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from constants.configs import DATABASE

"""
database.py

Async PostgreSQL helper for managing an image upscale job queue.

This module provides a Database class that wraps an asyncpg connection pool
and exposes high-level methods to create the schema, add jobs, claim the
next queued job (with row-level locking), update job states, and query jobs.

Environment:
- Expects a PostgreSQL connection string in the environment variable
  POSTGRE_CONN_STRING (loaded via python-dotenv when present).

Usage:
    db = Database()
    await db.connect()
    await db.init_schema()
    job_id = await db.add_job(...)
    next_job = await db.claim_next_queued_job()
    await db.close()
"""

load_dotenv()



class Database:
    """
    Asynchronous PostgreSQL database handler for an upscale job queue.

    This class manages an asyncpg connection pool and provides transactional
    operations suitable for a producer/consumer workflow where jobs are
    enqueued, claimed for processing with FOR UPDATE SKIP LOCKED semantics,
    and then marked as processing, completed, sent, or failed.

    Args:
        dsn: PostgreSQL DSN / connection string. If not provided, the module-level
             environment variable POSTGRE_CONN_STRING is used.

    Attributes:
        dsn: The database connection string.
        pool: An asyncpg.Pool instance once connect() has been called.
    """

    def __init__(self, dsn: str = DATABASE):
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """
        Establish an asyncpg connection pool.

        This must be called before performing any database operations. The pool
        is stored on the instance and reused for subsequent calls.

        Raises:
            asyncpg.PostgresError: If the connection or pool creation fails.
        """
        self.pool = await asyncpg.create_pool(self.dsn)

    async def close(self):
        """
        Close the connection pool gracefully.

        This should be awaited during application shutdown to ensure all
        connections are released back to the server.
        """
        if self.pool:
            await self.pool.close()

    async def init_schema(self):
        """
        Create the `upscale_jobs` table if it does not exist.

        The table schema contains columns to track job lifecycle, identify the
        submitting user and channel, store the source image URL, selected model,
        and where the processed output is saved.

        Raises:
            asyncpg.PostgresError: If the DDL statement fails.
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
            user_id: The ID of the user who requested the upscale.
            channel_id: The channel ID associated with the request.
            image_url: Source image URL to upscale.
            model_type: Identifier of the model to use for upscaling.
            token: Optional token associated with the request/provider.
            application_id: Optional application identifier.

        Returns:
            The generated job_id for the newly inserted job.

        Raises:
            asyncpg.PostgresError: If the insert fails.
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
        Atomically claim the next queued job for processing.

        This method selects the oldest job with status 'queued' and updates its
        status to 'processing' within the same transaction using
        FOR UPDATE SKIP LOCKED to avoid contention between consumers.

        Returns:
            A dictionary representing the claimed job (including job_id,
            user_id, channel_id, image_url, model_type, token, application_id)
            or None if there are no queued jobs.

        Raises:
            asyncpg.PostgresError: If the select/update transaction fails.
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
        Mark a job as being processed.

        Args:
            job_id: The job identifier.

        Raises:
            asyncpg.PostgresError: If the update fails.
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE upscale_jobs SET status = 'processing' WHERE job_id = $1",
                job_id,
            )

    async def mark_completed(self, job_id: int, output_path: str):
        """
        Mark a job as completed and record the output location.

        Args:
            job_id: The job identifier.
            output_path: Path or URL where the upscaled output is stored.

        Raises:
            asyncpg.PostgresError: If the update fails.
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
        Mark a job as failed and record a failure reason in output_path.

        Note: This implementation stores the failure reason in the output_path
        column to preserve a single text column. Adjust schema if you prefer a
        dedicated failure_reason column.

        Args:
            job_id: The job identifier.
            reason: Human-readable reason or error message describing the failure.

        Raises:
            asyncpg.PostgresError: If the update fails.
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
        Fetch all jobs that have been marked as completed.

        Returns:
            A list of dictionaries with keys: job_id, user_id, channel_id,
            image_url, model_type, status, output_path, created_at.

        Raises:
            asyncpg.PostgresError: If the select query fails.
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
        Mark a job as sent after delivering the completed output to the user.

        Args:
            job_id: The job identifier.

        Raises:
            asyncpg.PostgresError: If the update fails.
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE upscale_jobs SET status = 'sent' WHERE job_id = $1",
                job_id,
            )

    async def get_queue_position(self) -> int:
        """
        Return the total number of jobs currently in the queue or processing.

        This provides a simple view of current backlog size by counting jobs
        whose status is 'queued' or 'processing'.

        Returns:
            Integer count of jobs with status 'queued' or 'processing'.

        Raises:
            asyncpg.PostgresError: If the count query fails.
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM upscale_jobs
                WHERE status IN ('queued', 'processing')
                """
            )