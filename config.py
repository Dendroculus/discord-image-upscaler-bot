"""Configuration management for Discord Image Upscaler Bot."""
import os
from dotenv import load_dotenv

load_dotenv()

# Discord Configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# Upscaling Configuration
UPSCALE_FACTOR = int(os.getenv('UPSCALE_FACTOR', '2'))
MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', '8'))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Supported image formats
SUPPORTED_FORMATS = ['.png', '.jpg', '.jpeg', '.webp', '.gif']
