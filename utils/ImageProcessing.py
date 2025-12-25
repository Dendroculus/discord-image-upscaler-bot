import os
import cv2
import requests
import numpy as np
import torch
import gc
import shutil
import uuid
from PIL import Image
from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer
from typing import Optional
from constants.configs import General_Path, Anime_Path, MAX_IMAGE_DIMENSION

class AIUpscaler:
    """
    Wrapper around RealESRGAN that manages model loading, image downloading,
    preprocessing, and upscaling.

    This class implements memory-safe image handling by streaming downloads to disk
    and performing lazy resizing using Pillow before loading large bitmaps into RAM.
    It automatically manages VRAM caching and garbage collection for CUDA devices.

    Attributes:
        device (torch.device): The compute device (CUDA or CPU).
        use_half (bool): Flag indicating if half-precision (FP16) inference is enabled.
        _engines (dict): Cache for loaded RealESRGANer model instances.
    """

    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.use_half = True if self.device.type == "cuda" else False
        self._engines = {}
        print(f"🚀 AI Engine Initialized on: {self.device}")

    def _load_engine(self, model_type: str) -> RealESRGANer:
        """
        Loads the specified RealESRGAN model architecture and weights into memory.

        Args:
            model_type (str): The type of model to load ('anime' or 'general').

        Returns:
            RealESRGANer: The initialized inference engine.

        Raises:
            FileNotFoundError: If the model weights file does not exist.
        """
        if model_type == "anime":
            model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=6, num_grow_ch=32, scale=4)
            path = Anime_Path
        else:
            model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
            path = General_Path

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
        Retrieves a cached inference engine or loads it if not present.
        """
        if model_type not in self._engines:
            self._load_engine(model_type)
        return self._engines[model_type]

    def run_upscale(self, image_url: str, job_id: int, model_type: str = "general") -> Optional[bytes]:
        """
        Downloads, resizes (if necessary), and upscales an image from a URL.

        This method employs a safe pipeline:
        1. Streams the download to a temporary file to avoid RAM spikes.
        2. Uses Pillow to lazily check dimensions and resize large images before decoding.
        3. Converts to OpenCV format for the RealESRGAN engine.
        4. Runs inference and encodes the result as PNG bytes.

        Args:
            image_url (str): The URL of the source image.
            job_id (int): Unique identifier for logging purposes.
            model_type (str): The model variant to use ('general' or 'anime').

        Returns:
            Optional[bytes]: The upscaled image data in PNG format, or None if failed.
        """
        temp_filename = f"temp_{job_id}_{uuid.uuid4().hex[:8]}.png"
        
        try:
            if self.device.type == "cuda":
                torch.cuda.empty_cache()
                gc.collect()

            print(f"📥 Job #{job_id} - Downloading image stream...")
            with requests.get(image_url, stream=True) as r:
                r.raise_for_status()
                with open(temp_filename, 'wb') as f:
                    shutil.copyfileobj(r.raw, f)

            with Image.open(temp_filename) as pil_img:
                width, height = pil_img.size
                
                if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
                    print(f"⚠️ Job #{job_id} - Huge Image Detected ({width}x{height}). Resizing immediately via PILLOW.")
                    pil_img.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.Resampling.LANCZOS)
                
                if pil_img.mode != 'RGB':
                    pil_img = pil_img.convert('RGB')
                
                img = np.array(pil_img)
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

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

        except Exception as e:
            print(f"❌ Critical Error in AI Engine (Job #{job_id}): {e}")
            return None
        
        finally:
            if os.path.exists(temp_filename):
                try:
                    os.remove(temp_filename)
                except OSError:
                    pass
            
            if self.device.type == "cuda":
                torch.cuda.empty_cache()
                gc.collect()

engine = AIUpscaler()

def process_image(url: str, job_id: int, model_type: str) -> Optional[bytes]:
    """
    Module-level entry point to process an image using the singleton AIUpscaler instance.

    Args:
        url (str): The image URL.
        job_id (int): The job ID for logging.
        model_type (str): 'general' or 'anime'.

    Returns:
        Optional[bytes]: Upscaled PNG bytes or None.
    """
    return engine.run_upscale(url, job_id, model_type)