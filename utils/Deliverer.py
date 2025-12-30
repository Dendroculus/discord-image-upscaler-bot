import aiohttp
from azure.storage.blob.aio import BlobServiceClient
import re
from constants.configs import DISCORD_BOT_TOKEN, AZURE_STORAGE_BLOB, AZURE_CONTAINER_NAME, FILENAME
from constants.Emojis import customs

async def deliver_result(session: aiohttp.ClientSession, channel_id: int, image_data: bytes, user_id: int, model_type: str) -> bool:
    """
    Uploads raw image bytes to Azure Blob Storage and sends the link to Discord.
    """
    
    if not AZURE_STORAGE_BLOB:
        print("❌ Error: AZURE_STORAGE_BLOB connection string is missing in .env")
        return False

    
    CHANNEL_MSG_ENDPOINT = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}"}

    try:
        file_size_mb = len(image_data) / (1024 * 1024)
        print(f"☁️ Uploading {FILENAME} ({file_size_mb:.2f} MB) to Azure...")
        
        async with BlobServiceClient.from_connection_string(AZURE_STORAGE_BLOB) as blob_service_client:
            container_client = blob_service_client.get_container_client(AZURE_CONTAINER_NAME)
            
            blob_client = container_client.get_blob_client(FILENAME)
            
            await blob_client.upload_blob(image_data, overwrite=True)
            file_url = blob_client.url

        print(f"Upload success! Sending link to Discord: {file_url}")
        
        emoji_str = customs["download"]
        emoji_payload = {"name": emoji_str}
    
        match = re.search(r":(\w+):(\d+)>", emoji_str)
        if match:
            emoji_payload = {
                "name": match.group(1), 
                "id": match.group(2)    
            }
            
        payload = {
            "content": f"(●'◡'●) here's your UpScaled image <@{user_id}>! Mode: `{model_type.capitalize()}`",
            "embeds": [{
                "title": "✨ Upscale Successful",
                "color": 5763719, 
                "image": {"url": file_url},
            }],
            "components": [
                {
                    "type": 1,  
                    "components": [
                        {
                            "type": 2,       
                            "style": 5,     
                            "label": "Download Full Image",
                            "url": file_url, 
                            "emoji": emoji_payload
                        }
                    ]
                }
            ]
        }

        async with session.post(CHANNEL_MSG_ENDPOINT, headers=headers, json=payload) as resp:
            await resp.read() 
            if resp.status != 200:
                error_text = await resp.text()
                print(f"⚠️ Discord Message Error: {error_text}")
                return False
            return True

    except Exception as e:
        print(f"❌ Delivery Error: {e}")
        return False