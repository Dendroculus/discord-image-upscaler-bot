import os

class ModelRegistry:
    """
    Central source of truth for available AI models.
    Decouples model definitions from file paths.
    """
    BASE_DIRECTORY = "models"

    _MODELS = {
        "general": "RealESRGAN_x4plus.pth",
        "anime": "RealESRGAN_x4plus_anime_6B.pth",
    }

    @classmethod
    def get_path(cls, model_type: str) -> str:
        """
        Dynamically resolves the file path for a given model type.
        """
        filename = cls._MODELS.get(model_type)
        
        if not filename:
            # This protects your app from crashing with vague errors
            raise ValueError(f"Model type '{model_type}' is not registered.")
            
        return os.path.join(cls.BASE_DIRECTORY, filename)

    @classmethod
    def list_models(cls):
        """Returns a list of available model keys."""
        return list(cls._MODELS.keys())