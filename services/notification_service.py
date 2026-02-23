import aiohttp
import re
from constants.configs import DISCORD_BOT_TOKEN
from constants.emojis import customs

class NotificationService:
    @staticmethod
    async def send_delivery_message(session: aiohttp.ClientSession, channel_id: int, user_id: int, model_type: str, file_url: str):
        """
        Inform the user via Discord that their upscaled image is successfully ready.
        """
        endpoint = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}"}

        emoji_str = customs["download"]
        emoji_payload = {"name": emoji_str}
        match = re.search(r":(\w+):(\d+)>", emoji_str)
        if match:
            emoji_payload = {"name": match.group(1), "id": match.group(2)}
            
        payload = {
            "content": f"(●'◡'●) here's your UpScaled image <@{user_id}>! Mode: `{model_type.capitalize()}`",
            "embeds": [{
                "title": "✨ Upscale Successful",
                "color": 5763719, 
                "image": {"url": file_url},
            }],
            "components": [{
                "type": 1,
                "components": [{
                    "type": 2,
                    "style": 5,
                    "label": "Download Full Image",
                    "url": file_url,
                    "emoji": emoji_payload
                }]
            }]
        }

        async with session.post(endpoint, headers=headers, json=payload) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise RuntimeError(f"Discord API Error {resp.status}: {error_text}")