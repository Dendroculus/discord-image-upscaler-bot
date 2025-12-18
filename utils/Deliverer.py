import os
import aiohttp

async def deliver_result(channel_id: int, file_path: str, user_id: int, model_type: str) -> bool:
    """
    Utility function to upload a file directly to a Discord channel.
    Can be called by any worker on any server.
    """
    token = os.getenv("DISCORD_TOKEN")
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {"Authorization": f"Bot {token}"}
    
    async with aiohttp.ClientSession() as session:
        try:
            with open(file_path, 'rb') as f:
                data = aiohttp.FormData()
                data.add_field('payload_json', f'{{"content": "Done <@{user_id}>! Mode: {model_type}"}}')
                data.add_field('file', f, filename=os.path.basename(file_path))
                
                async with session.post(url, headers=headers, data=data) as resp:
                    return resp.status == 200
        except Exception as e:
            print(f"❌ Delivery Error: {e}")
            return False