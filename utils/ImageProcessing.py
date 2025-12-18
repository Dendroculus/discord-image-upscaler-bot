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

Thin wrapper around the Real-ESRGAN upscaling engine.

Module responsibilities and logic flow:
1. Initialize a persistent AIUpscaler that:
   - defines model paths for "general" and "anime" models,
   - chooses a compute device (CUDA if available) and precision mode,
   - lazily loads and caches RealESRGANer engine instances per model type.
2. For each upscaling request:
   - download the image bytes from the provided URL,
   - decode into an OpenCV image,
   - pick a tile size based on input dimensions to reduce memory usage on large images,
   - reuse (or load) the appropriate RealESRGANer engine and set dynamic tiling,
   - run the enhance call to obtain the upscaled image,
   - write the result to the configured output folder and return the filesystem path.
3. On errors, log and return None to indicate failure; callers should treat None as a failed processing attempt.

Note: The module exposes a singleton `engine` and a convenience `process_image` wrapper.
"""

class AIUpscaler:
    """
    Engine wrapper managing model file locations, device selection, and execution.

    Attributes:
        model_path_general: Path to the general photo model file.
        model_path_anime: Path to the anime model file.
        output_folder: Directory for saving upscaled images.
        device: torch device selected (cuda or cpu).
        use_half: Whether to use FP16 (only on CUDA).
        _engines: cache mapping model_type to loaded RealESRGANer instances.

    Logic flow for run_upscale:
    1. Download bytes from the URL and decode to an image.
    2. Determine tiling size heuristically based on dimensions.
    3. Obtain (and potentially load) the engine for the requested model.
    4. Adjust engine.tile dynamically for the current image to avoid reloads.
    5. Call enhance() to produce the upscaled image and save it to disk.
    6. If CUDA is used, clear cache and collect garbage to free memory.
    7. Return the saved file path or None on failure.
    """

    def __init__(self):
        self.model_path_general = os.path.join("models", "RealESRGAN_x4plus.pth")
        self.model_path_anime = os.path.join("models", "RealESRGAN_x4plus_anime_6B.pth")
        self.output_folder = "output"
        os.makedirs(self.output_folder, exist_ok=True)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.use_half = True if self.device.type == "cuda" else False
        self._engines = {}
        print(f"🚀 AI Engine Initialized on: {self.device}")

    def _load_engine(self, model_type: str) -> RealESRGANer:
        """
        Load and cache a RealESRGANer instance for the given model_type.

        Raises:
            FileNotFoundError: if the model file is not present on disk.
        """
        if model_type == "anime":
            model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=6, num_grow_ch=32, scale=4)
            path = self.model_path_anime
        else:
            model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
            path = self.model_path_general

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
        Return a cached engine instance, loading it if necessary.
        """
        if model_type not in self._engines:
            self._load_engine(model_type)
        return self._engines[model_type]

    def run_upscale(self, image_url: str, job_id: int, model_type: str = "general") -> str | None:
         # personal NOTE: str | none is same as Optional[str]
        """
        Download an image, run upscaling, save the file, and return its path.

        Returns:
            The filesystem path to the saved upscaled image, or None on failure.
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

            upsampler = self._get_engine(model_type)
            # Adjust tiling dynamically without reloading the model
            upsampler.tile = tile_size

            print(f"⚡ Job #{job_id} - Processing ({model_type})...")
            output_img, _ = upsampler.enhance(img, outscale=4)

            filename = f"upscaled_{uuid.uuid4().hex[:8]}.png"
            save_path = os.path.join(self.output_folder, filename)
            cv2.imwrite(save_path, output_img)

            if self.device.type == "cuda":
                torch.cuda.empty_cache()
                gc.collect()

            return save_path

        except Exception as e:
            print(f"❌ Critical Error in AI Engine (Job #{job_id}): {e}")
            return None


engine = AIUpscaler()


def process_image(url: str, job_id: int, model_type: str) -> str:
    """
    Convenience wrapper that delegates to the singleton AIUpscaler.

    Returns:
        Output path string on success or None on failure.
    """
    return engine.run_upscale(url, job_id, model_type)