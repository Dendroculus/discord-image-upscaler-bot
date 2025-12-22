import os
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE = os.getenv("POSTGRE_CONN_STRING")
AZURE_STORAGE_BLOB = os.getenv("AZURE_CONNECTION_STRING")
MAX_IMAGE_DIMENSION = 1280

Models = {
    "General": "RealESRGAN_x4plus.pth",
    "Anime": "RealESRGAN_x4plus_anime_6B.pth",
}

General_Path = os.path.join("models", Models["General"])
Anime_Path = os.path.join("models", Models["Anime"])

