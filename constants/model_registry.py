"""
model_registry.py

Provides a central source of truth for all available AI models.
Responsibility: Decouples model definitions, file paths, and network architectures
from the rest of the application to prevent configuration drift.
"""
import os
from typing import Dict, Any, List

class ModelRegistry:
    """
    Central source of truth for available AI models.
    Decouples model definitions from file paths.
    """
    BASE_DIRECTORY = "models"

    _MODELS = {
        "general": {
            "path": "RealESRGAN_x4plus.pth",
            "arch": {"num_in_ch": 3, "num_out_ch": 3, "num_feat": 64, "num_block": 23, "num_grow_ch": 32, "scale": 4}
        },
        "anime": {
            "path": "RealESRGAN_x4plus_anime_6B.pth",
            "arch": {"num_in_ch": 3, "num_out_ch": 3, "num_feat": 64, "num_block": 6, "num_grow_ch": 32, "scale": 4}
        },
    }

    @classmethod
    def get_path(cls, model_type: str) -> str:
        """
        Dynamically resolves the file path for a given model type.
        
        Args:
            model_type (str): The string identifier of the model.
            
        Returns:
            str: The resolved local file path for the model weights.
            
        Raises:
            ValueError: If the requested model type is not registered.
        """
        model_info = cls._MODELS.get(model_type)
        
        if not model_info:
            raise ValueError(f"Model type '{model_type}' is not registered.")
            
        return os.path.join(cls.BASE_DIRECTORY, model_info["path"])
        
    @classmethod
    def get_arch(cls, model_type: str) -> Dict[str, Any]:
        """
        Retrieves the network architecture configuration for a given model type.
        
        Args:
            model_type (str): The string identifier of the model.
            
        Returns:
            Dict[str, Any]: The keyword arguments needed to instantiate the model network.
            
        Raises:
            ValueError: If the requested model type is not registered.
        """
        model_info = cls._MODELS.get(model_type)
        
        if not model_info:
            raise ValueError(f"Model type '{model_type}' is not registered.")
            
        return model_info["arch"]

    @classmethod
    def list_models(cls) -> List[str]:
        """
        Returns a list of available model keys.
        
        Returns:
            List[str]: A list containing the registered model identifiers.
        """
        return list(cls._MODELS.keys())