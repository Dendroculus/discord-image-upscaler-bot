import os
import cv2
import requests
import numpy as np
import uuid
import torch
import gc
from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer

"""
ImageProcessing.py

Provides a thin wrapper around the Real-ESRGAN upscaling engine.

The module exposes:
- AIUpscaler: a persistent engine instance that loads model files and runs
  upscaling on images fetched from URLs.
- process_image: simple convenience function used by worker.py to invoke the engine.

The output images are written to the configured output folder and the path is
returned for further delivery or cleanup.
"""


class AIUpscaler:
    """
    Engine wrapper that manages model file paths, device selection, and execution.

    Attributes:
        model_path_general (str): Filesystem path to the general model file.
        model_path_anime (str): Filesystem path to the anime model file.
        output_folder (str): Directory to write resulting upscaled images.
        device (torch.device): Selected compute device (CUDA if available).
        use_half (bool): Whether to use FP16 half precision on CUDA.
    """

    def __init__(self):
        """
        Initialize the upscaler with model paths, output folder, and device.
        """
        self.model_path_general = os.path.join("models", "RealESRGAN_x4plus.pth")
        self.model_path_anime = os.path.join("models", "RealESRGAN_x4plus_anime_6B.pth")
        self.output_folder = "output"
        os.makedirs(self.output_folder, exist_ok=True)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.use_half = True if self.device.type == "cuda" else False
        print(f"🚀 AI Engine Initialized on: {self.device}")

    def _get_model_instance(self, model_type: str, tile_size: int = 0) -> RealESRGANer:
        """
        Construct and return a RealESRGANer instance for the requested model type.

        Args:
            model_type: 'anime' selects the anime model; any other value selects the general model.
            tile_size: Tile size to use for tiled processing (0 = no tiling).

        Returns:
            An initialized RealESRGANer instance ready to perform `enhance`.
        """
        if model_type == "anime":
            model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=6, num_grow_ch=32, scale=4)
            path = self.model_path_anime
        else:
            model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
            path = self.model_path_general

        if not os.path.exists(path):
            raise FileNotFoundError(f"Model file missing: {path}")

        return RealESRGANer(
            scale=4,
            model_path=path,
            model=model,
            tile=tile_size,
            tile_pad=10,
            pre_pad=0,
            half=self.use_half,
            device=self.device,
        )

    def run_upscale(self, image_url: str, job_id: int, model_type: str = "general") -> str:
        """
        Download an image from a URL, run the Real-ESRGAN upscaler, save the result,
        and return the filesystem path to the saved image.

        Args:
            image_url: Public URL of the source image.
            job_id: Numeric job identifier used for logging.
            model_type: Model selection string, e.g. 'general' or 'anime'.

        Returns:
            The path to the saved upscaled image on success.

        Raises:
            ConnectionError: If the image cannot be downloaded.
            ValueError: If the downloaded data cannot be decoded as an image.
            FileNotFoundError: If the configured model file is missing.
            RuntimeError: For other processing problems.
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
            tile_size = 400 if (height > 1000 or width > 1000) else 0

            upsampler = self._get_model_instance(model_type, tile_size)
            print(f"⚡ Job #{job_id} - Processing ({model_type})...")
            output_img, _ = upsampler.enhance(img, outscale=4)

            filename = f"upscaled_{uuid.uuid4().hex[:8]}.png"
            save_path = os.path.join(self.output_folder, filename)
            cv2.imwrite(save_path, output_img)

            if self.device.type == "cuda":
                del upsampler
                torch.cuda.empty_cache()
                gc.collect()

            return save_path

        except Exception as e:
            print(f"❌ Critical Error in AI Engine (Job #{job_id}): {e}")
            return None


engine = AIUpscaler()


def process_image(url: str, job_id: int, model_type: str) -> str:
    """
    Convenience wrapper around the singleton AIUpscaler instance.

    Args:
        url: The image URL to process.
        job_id: Job identifier.
        model_type: Model variant to use.

    Returns:
        Filesystem path of the generated image, or None on failure.
    """
    return engine.run_upscale(url, job_id, model_type)