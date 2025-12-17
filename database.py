import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

DB_DSN = os.getenv("POSTGRE_CONN_STRING")

async def get_db_pool():
    return await asyncpg.create_pool(DB_DSN)


async def init_db(pool):
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS upscale_jobs (
                job_id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                image_url TEXT NOT NULL,
                model_type TEXT NOT NULL,
                status TEXT DEFAULT 'queued',
                output_path TEXT,  
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        
async def add_job(pool, user_id, image_url, model_type):
    async with pool.acquire() as conn:
        job_id = await conn.fetchval("""
            INSERT INTO upscale_jobs (user_id, image_url, model_type)
            VALUES ($1, $2, $3)
            RETURNING job_id
        """, user_id, image_url, model_type)
        return job_id

async def get_completed_jobs(pool):
    """Fetch all jobs that the worker has finished but the bot hasn't sent yet."""
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT * FROM upscale_jobs WHERE status = 'completed'")

async def mark_job_sent(pool, job_id):
    """Mark the job as 'sent' so we don't spam the user."""
    async with pool.acquire() as conn:
        await conn.execute("UPDATE upscale_jobs SET status = 'sent' WHERE job_id = $1", job_id)