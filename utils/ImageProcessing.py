import os
import cv2
import requests
import numpy as np
import torch
import gc
from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer
from typing import Optional

class AIUpscaler:
    def __init__(self):
        self.model_path_general = os.path.join("models", "RealESRGAN_x4plus.pth")
        self.model_path_anime = os.path.join("models", "RealESRGAN_x4plus_anime_6B.pth")
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.use_half = True if self.device.type == "cuda" else False
        self._engines = {}
        print(f"🚀 AI Engine Initialized on: {self.device}")

    def _load_engine(self, model_type: str) -> RealESRGANer:
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
        if model_type not in self._engines:
            self._load_engine(model_type)
        return self._engines[model_type]

    def run_upscale(self, image_url: str, job_id: int, model_type: str = "general") -> Optional[bytes]:
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

            print(f"⚡ Job #{job_id} - Processing ({model_type})...")
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
    return engine.run_upscale(url, job_id, model_type)