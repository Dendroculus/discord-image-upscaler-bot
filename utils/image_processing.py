import os
import cv2
import requests
import numpy as np
import uuid
import torch
import gc
from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer

class AIUpscaler:
    """
    A production-grade wrapper for Real-ESRGAN that handles model loading,
    smart-tiling for large images, and GPU acceleration.
    """

    def __init__(self):
        """
        Initializes the AI engine, detects GPU, and creates output directories.
        """
        # Paths to your model weights
        self.model_path_general = os.path.join("models", "RealESRGAN_x4plus.pth")
        self.model_path_anime = os.path.join("models", "RealESRGAN_x4plus_anime_6B.pth")
        
        # Output setup
        self.output_folder = "output"
        os.makedirs(self.output_folder, exist_ok=True)
        
        # Hardware Check
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.use_half = True if self.device.type == 'cuda' else False
        
        print(f"🚀 AI Engine Initialized on: {self.device} (Precision: {'Half' if self.use_half else 'Full'})")

    def _get_model_instance(self, model_type: str, tile_size: int = 0) -> RealESRGANer:
        """
        Instantiates the RealESRGANer with the correct weights and tiling settings.

        Args:
            model_type (str): 'anime' or 'general'.
            tile_size (int): 0 for no tiling (fastest), 200-400 for low VRAM.

        Returns:
            RealESRGANer: The configured upsampler instance.
        """
        if model_type == 'anime':
            # Anime 6B is smaller (6 blocks)
            model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=6, num_grow_ch=32, scale=4)
            path = self.model_path_anime
        else:
            # General x4plus is larger (23 blocks)
            model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
            path = self.model_path_general

        if not os.path.exists(path):
            raise FileNotFoundError(f"Model file missing: {path}")

        upsampler = RealESRGANer(
            scale=4,
            model_path=path,
            model=model,
            tile=tile_size,
            tile_pad=10,
            pre_pad=0,
            half=self.use_half,
            device=self.device
        )
        return upsampler

    def run_upscale(self, image_url: str, model_type: str = 'general') -> str:
        """
        Downloads, processes, and saves the upscaled image.

        Args:
            image_url (str): The Discord attachment URL.
            model_type (str): The user's choice ('general' or 'anime').

        Returns:
            str: Path to the saved file on success, None on failure.
        """
        try:
            # 1. Download
            print(f"📥 Downloading: {image_url}...")
            resp = requests.get(image_url, stream=True)
            if resp.status_code != 200:
                raise ConnectionError(f"Failed to download image: {resp.status_code}")
            
            # 2. Decode
            image_array = np.asarray(bytearray(resp.content), dtype=np.uint8)
            img = cv2.imdecode(image_array, cv2.IMREAD_UNCHANGED)
            if img is None:
                raise ValueError("Could not decode image bytes.")

            # 3. Dynamic Tiling Strategy (Scalability)
            # If image is large (>1000px height or width), use tiling to prevent crash
            height, width = img.shape[:2]
            tile_size = 0 
            if height > 1000 or width > 1000:
                print(f"⚠️ Large Image detected ({width}x{height}). Enabling tiling mode.")
                tile_size = 400 

            # 4. Load Model
            upsampler = self._get_model_instance(model_type, tile_size)
            
            print(f"⚡ Processing with {model_type} model...")
            output_img, _ = upsampler.enhance(img, outscale=4)

            # 5. Save
            filename = f"upscaled_{uuid.uuid4().hex[:8]}.png"
            save_path = os.path.join(self.output_folder, filename)
            cv2.imwrite(save_path, output_img)
            
            # 6. Cleanup GPU Memory
            if self.device.type == 'cuda':
                del upsampler
                torch.cuda.empty_cache()
                gc.collect()

            print(f"✅ Saved to: {save_path}")
            return save_path

        except Exception as e:
            print(f"❌ Critical Error in AI Engine: {e}")
            return None

# --- Singleton Instance ---
engine = AIUpscaler()

def process_image(url: str, model_type: str) -> str:
    """Public API for worker.py to call."""
    return engine.run_upscale(url, model_type)