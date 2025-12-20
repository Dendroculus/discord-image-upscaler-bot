from os import getenv
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = getenv("DISCORD_TOKEN")
DATABASE = getenv("POSTGRE_CONN_STRING")
AZURE_STORAGE_BLOB = getenv("AZURE_CONNECTION_STRING")