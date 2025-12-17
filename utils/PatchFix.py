import sys
import types
import torchvision

def patch_torchvision():
    """Patch torchvision to ensure compatibility with certain environments."""
    if not hasattr(torchvision.transforms, 'functional_tensor'):
        from torchvision.transforms import functional as functional_new
        module = types.ModuleType("torchvision.transforms.functional_tensor")
        module.rgb_to_grayscale = functional_new.rgb_to_grayscale
        sys.modules["torchvision.transforms.functional_tensor"] = module
        
patch_torchvision()