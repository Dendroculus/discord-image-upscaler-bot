import os
import cv2
import requests
import numpy as np
import torch
import gc
from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer
from typing import Optional
from constants.configs import General_Path, Anime_Path

class AIUpscaler:
    """
    Wrapper around RealESRGAN that downloads images and performs upscaling.

    This class manages model paths, device selection, engine caching, and
    the upscaling pipeline. It exposes a `run_upscale` method which downloads
    an image from a URL, runs the selected RealESRGAN model, and returns the
    result as PNG-encoded bytes.

    Attributes:
        model_path_general (str): Path to the general RealESRGAN model file.
        model_path_anime (str): Path to the anime RealESRGAN model file.
        device (torch.device): Torch device used for inference ('cuda' or 'cpu').
        use_half (bool): Whether to use half precision (fp16) on CUDA.
        _engines (dict): Cached RealESRGANer instances keyed by model type.
    """

    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.use_half = True if self.device.type == "cuda" else False
        self._engines = {}
        print(f"🚀 AI Engine Initialized on: {self.device}")

    def _load_engine(self, model_type: str) -> RealESRGANer:
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
        if model_type not in self._engines:
            self._load_engine(model_type)
        return self._engines[model_type]

    def run_upscale(self, image_url: str, job_id: int, model_type: str = "general") -> Optional[bytes]:
        """
        Download an image from `image_url`, upscale it using RealESRGAN, and return PNG bytes.

        Args:
            image_url (str): URL of the image to download and upscale.
            job_id (int): Identifier used for logging/debugging.
            model_type (str): Which model to use; 'general' or 'anime'. Defaults to 'general'.

        Returns:
            Optional[bytes]: PNG-encoded bytes of the upscaled image on success, or None on failure.
        """
        try:
            print(f"📥 Job #{job_id} - Downloading image...")
            resp = requests.get(image_url, stream=True)
            if resp.status_code != 200:
                raise ConnectionError(f"Download failed: {resp.status_code}")

            image_array = np.asarray(bytearray(resp.content), dtype=np.uint8)
            img = cv2.imdecode(image_array, cv2.IMREAD_UNCHANGED)
            if img is None:
                raise ValueError("Could not decode image.")

            height, width = img.shape[:2]
            tile_size = 256 if (height > 800 or width > 800) else 0

            upsampler = self._get_engine(model_type)
            upsampler.tile = tile_size

            print(f" ⚒️ Job #{job_id} - Processing ({model_type})...")
            output_img, _ = upsampler.enhance(img, outscale=4)

            success, buffer = cv2.imencode(".png", output_img)
            if not success:
                raise ValueError("Could not encode output image to PNG.")

            if self.device.type == "cuda":
                torch.cuda.empty_cache()
                gc.collect()

            return buffer.tobytes()

        except Exception as e:
            print(f"❌ Critical Error in AI Engine (Job #{job_id}): {e}")
            return None

engine = AIUpscaler()

def process_image(url: str, job_id: int, model_type: str) -> Optional[bytes]:
    """
    Convenience wrapper that uses the module-level AIUpscaler to process an image URL.

    Args:
        url (str): URL of the image to upscale.
        job_id (int): Job identifier for logging.
        model_type (str): Model type to use ('general' or 'anime').

    Returns:
        Optional[bytes]: PNG-encoded bytes of the upscaled image, or None on error.
    """
    return engine.run_upscale(url, job_id, model_type)