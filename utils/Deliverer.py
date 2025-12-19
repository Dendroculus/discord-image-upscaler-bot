import os
import aiohttp
import uuid
from azure.storage.blob.aio import BlobServiceClient

async def deliver_result(channel_id: int, image_data: bytes, user_id: int, model_type: str) -> bool:
    """
    Uploads raw image bytes to Azure Blob Storage and sends the link to Discord.
    """
    connection_string = os.getenv("AZURE_CONNECTION_STRING")
    discord_token = os.getenv("DISCORD_TOKEN")
    container_name = "images" # NOTE :  This container must exist in Azure Blob Storage
    
    if not connection_string:
        print("❌ Error: AZURE_CONNECTION_STRING is missing in .env")
        return False

    filename = f"upscaled_{uuid.uuid4().hex[:8]}.png"
    
    discord_api_url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {"Authorization": f"Bot {discord_token}"}

    try:
        file_size_mb = len(image_data) / (1024 * 1024)
        print(f"☁️ Uploading {filename} ({file_size_mb:.2f} MB) to Azure...")
        
        async with BlobServiceClient.from_connection_string(connection_string) as blob_service_client:
            container_client = blob_service_client.get_container_client(container_name)
            
            blob_client = container_client.get_blob_client(filename)
            
            await blob_client.upload_blob(image_data, overwrite=True)
            file_url = blob_client.url

        print(f"Upload success! Sending link to Discord: {file_url}")
        
        payload = {
            "content": f"(●'◡'●) here's your UpScaled image <@{user_id}>! \nMode: `{model_type.capitalize()}`",
            "embeds": [{
                "image": {"url": file_url},
            }]
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(discord_api_url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    print(f"⚠️ Discord Message Error: {error_text}")
                    return False
                return True

    except Exception as e:
        print(f"❌ Delivery Error: {e}")
        return False