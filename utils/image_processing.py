"""
image_processing.py

Handles the core AI upscaling logic using RealESRGAN.
Responsibility: Downloads, preprocesses, and upscales images utilizing 
PyTorch and RealESRGAN models while managing GPU memory efficiently.
"""
import os
import cv2
import aiohttp
import asyncio
import numpy as np
import torch
import gc
import uuid
from PIL import Image
from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer
from typing import Optional
from constants.configs import MAX_IMAGE_DIMENSION
from constants.model_registry import ModelRegistry

class AIUpscaler:
    """
    Manages the RealESRGAN inference pipeline with memory-safe image handling.

    This class handles the lifecycle of the AI models, including loading, caching,
    and execution. It implements a resource-guarded pipeline that prioritizes
    system stability by:
    1. Streaming large downloads to disk to prevent RAM spikes.
    2. Lazily inspecting and resizing images via Pillow before loading into memory.
    3. Managing GPU VRAM allocation and garbage collection.

    Attributes:
        device (torch.device): The active compute device (CUDA/CPU).
        use_half (bool): Enabled if CUDA is available for FP16 precision.
        _engines (dict): Runtime cache for loaded model architectures.
    """

    def __init__(self):
        """
        Initializes the AIUpscaler and detects available compute devices.
        """
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.use_half = True if self.device.type == "cuda" else False
        self._engines = {}
        print(f"🚀 AI Engine Initialized on: {self.device}")

    def _load_engine(self, model_type: str) -> RealESRGANer:
        """
        Initializes and loads specific RealESRGAN weights into memory.

        Args:
            model_type (str): Identifier for the model.

        Returns:
            RealESRGANer: The configured inference engine instance.

        Raises:
            FileNotFoundError: If the model weight file is missing from the disk.
        """
        arch_config = ModelRegistry.get_arch(model_type)
        path = ModelRegistry.get_path(model_type)
        
        model = RRDBNet(**arch_config)

        if not os.path.exists(path):
            raise FileNotFoundError(f"Model file missing: {path}")

        engine = RealESRGANer(
            scale=4,
            model_path=path,
            model=model,
            tile=0,
            tile_pad=10,
            pre_pad=0,
            half=self.use_half,
            device=self.device,
        )
        self._engines[model_type] = engine
        return engine

    def _get_engine(self, model_type: str) -> RealESRGANer:
        """
        Retrieves a cached model instance or loads it on demand.
        
        Args:
            model_type (str): Identifier for the model.
            
        Returns:
            RealESRGANer: The configured inference engine instance.
        """
        if model_type not in self._engines:
            self._load_engine(model_type)
        return self._engines[model_type]

    async def _download_image(self, url: str, job_id: int, session: aiohttp.ClientSession) -> str:
        """
        Streams an image from a URL to a temporary file asynchronously.

        Using streaming prevents loading the entire raw file into RAM at once,
        which safeguards against large file downloads.

        Args:
            url (str): The source URL.
            job_id (int): Job identifier for logging context.
            session (aiohttp.ClientSession): The asynchronous HTTP client session.

        Returns:
            str: The local filepath of the downloaded temporary file.
        """
        temp_filename = f"temp_{job_id}_{uuid.uuid4().hex[:8]}.png"
        print(f"📥 Job #{job_id} - Downloading image stream...")
        
        async with session.get(url) as r:
            r.raise_for_status()
            with open(temp_filename, 'wb') as f:
                async for chunk in r.content.iter_chunked(8192):
                    f.write(chunk)
        
        return temp_filename

    def _load_and_preprocess(self, temp_filename: str, job_id: int) -> np.ndarray:
        """
        Reads the image file, resizes it if necessary, and converts to BGR format.

        This method uses Pillow to open the image header (lazy loading). If dimensions
        exceed MAX_IMAGE_DIMENSION, it downscales the image using Lanczos resampling
        before decoding the full pixel data to prevent OOM errors.

        Args:
            temp_filename (str): Path to the temporary image file.
            job_id (int): Job identifier for logging context.

        Returns:
            np.ndarray: The processed image in OpenCV (BGR) format.
        """
        with Image.open(temp_filename) as pil_img:
            width, height = pil_img.size
            
            if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
                print(f"⚠️ Job #{job_id} - Huge Image ({width}x{height}). Resizing...")
                pil_img.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.Resampling.LANCZOS)
            
            if pil_img.mode != 'RGB':
                pil_img = pil_img.convert('RGB')
            
            img = np.array(pil_img)
            return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    def _run_inference(self, img: np.ndarray, model_type: str, job_id: int) -> bytes:
        """
        Executes the AI model on the input image.

        Args:
            img (np.ndarray): Input image in BGR format.
            model_type (str): The model variant to use.
            job_id (int): Job identifier for logging context.

        Returns:
            bytes: The upscaled result encoded as a PNG byte stream.

        Raises:
            ValueError: If image encoding fails.
        """
        height, width = img.shape[:2]
        tile_size = 192 if (height > 600 or width > 600) else 0

        upsampler = self._get_engine(model_type)
        upsampler.tile = tile_size
        
        upsampler.model.to(self.device)
        if self.use_half:
            upsampler.model.half()
        upsampler.half = self.use_half

        print(f" ⚒️ Job #{job_id} - Processing ({model_type}) [Size: {width}x{height}] [Tile: {tile_size}]...")
        
        output_img, _ = upsampler.enhance(img, outscale=4)

        success, buffer = cv2.imencode(".png", output_img)
        if not success:
            raise ValueError("Could not encode output image to PNG.")
        
        return buffer.tobytes()

    def _cleanup_resources(self, temp_filename: Optional[str]):
        """
        Removes temporary files and forces CUDA garbage collection.

        Args:
            temp_filename (Optional[str]): Path to the file to delete.
        """
        if temp_filename and os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except OSError:
                pass
        
        if self.device.type == "cuda":
            torch.cuda.empty_cache()
            gc.collect()

    async def run_upscale(self, image_url: str, job_id: int, model_type: str, session: aiohttp.ClientSession) -> Optional[bytes]:
        """
        Orchestrates the complete upscaling pipeline asynchronously.

        Sequence:
        1. Clean VRAM.
        2. Stream download image to disk.
        3. Preprocess (resize/format).
        4. Run Inference.
        5. Cleanup resources.

        Args:
            image_url (str): URL of the image to upscale.
            job_id (int): Unique identifier for the job.
            model_type (str): 'general' or 'anime'.
            session (aiohttp.ClientSession): Active HTTP session.

        Returns:
            Optional[bytes]: The PNG image data, or None if an error occurred.
        """
        temp_filename = None
        try:
            if self.device.type == "cuda":
                torch.cuda.empty_cache()
                gc.collect()

            temp_filename = await self._download_image(image_url, job_id, session)
            img_array = await asyncio.to_thread(self._load_and_preprocess, temp_filename, job_id)
            result_bytes = await asyncio.to_thread(self._run_inference, img_array, model_type, job_id)
            
            return result_bytes

        except Exception as e:
            print(f"❌ Critical Error in AI Engine (Job #{job_id}): {e}")
            return None
        
        finally:
            self._cleanup_resources(temp_filename)