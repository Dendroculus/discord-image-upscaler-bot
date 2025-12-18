import os
import aiohttp
import aiofiles
import aiofiles.os

async def deliver_result(channel_id: int, file_path: str, user_id: int, model_type: str) -> bool:
    """
    Utility function to upload a file directly to a Discord channel.
    Uses streaming to handle large AI-generated images without high RAM usage.
    """
    token = os.getenv("DISCORD_TOKEN")
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {"Authorization": f"Bot {token}"}

    async def file_sender(path):
        async with aiofiles.open(path, 'rb') as f:
            while chunk := await f.read(64 * 1024):
                yield chunk

    try:
        stat = await aiofiles.os.stat(file_path)
        file_size = stat.st_size
        
        if file_size > 10 * 1024 * 1024: # 10 MB Limit
            print(f"❌ File too large ({file_size / (1024*1024):.2f}MB). Please make sure it is under 10MB.")
            return False

        async with aiohttp.ClientSession() as session:
            data = aiohttp.FormData()
            data.add_field('payload_json', f'{{"content": "Done <@{user_id}>! Mode: {model_type}"}}')
            
            data.add_field(
                'file', 
                file_sender(file_path), 
                filename=os.path.basename(file_path)
            )

            async with session.post(url, headers=headers, data=data) as resp:
                if resp.status != 200:
                    err_msg = await resp.text()
                    print(f"⚠️ Discord Upload Error: {resp.status} - {err_msg}")
                return resp.status == 200

    except Exception as e:
        print(f"❌ Delivery Error: {e}")
        return False