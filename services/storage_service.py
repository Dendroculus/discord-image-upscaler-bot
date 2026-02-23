from azure.storage.blob.aio import BlobServiceClient
from constants.configs import AZURE_STORAGE_BLOB, AZURE_CONTAINER_NAME, FILENAME

class StorageService:
    @staticmethod
    async def upload_file(image_data: bytes) -> str:
        """
        Uploads bytes to Azure Blob Storage and returns the public URL.
        """
        if not AZURE_STORAGE_BLOB:
            raise ValueError("AZURE_STORAGE_BLOB is missing in .env")

        file_size_mb = len(image_data) / (1024 * 1024)
        print(f"☁️ Uploading {FILENAME} ({file_size_mb:.2f} MB) to Azure...")

        async with BlobServiceClient.from_connection_string(AZURE_STORAGE_BLOB) as blob_service_client:
            container_client = blob_service_client.get_container_client(AZURE_CONTAINER_NAME)
            blob_client = container_client.get_blob_client(FILENAME)
            
            await blob_client.upload_blob(image_data, overwrite=True)
            return blob_client.url