import os
from dotenv import load_dotenv
import uuid

load_dotenv()
DISCORD_BOT_TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE = os.getenv("POSTGRE_CONN_STRING")
AZURE_STORAGE_BLOB = os.getenv("AZURE_CONNECTION_STRING")

MAX_IMAGE_DIMENSION = 1280
MAX_IMAGE_SIZE = 8 * 1024 * 1024  # 8 MB
FILENAME = f"upscaled_{uuid.uuid4().hex[:8]}.png"
AZURE_CONTAINER_NAME = "images"  # NOTE: This container must exist and be named exactly "images" in Azure Blob Storage