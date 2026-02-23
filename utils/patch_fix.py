import sys
import types
import torchvision

"""
PatchFix.py

Compatibility shim for torchvision.

Purpose and logic flow:
1. Some older code expects `torchvision.transforms.functional_tensor` to exist.
2. If that attribute is missing in the installed torchvision, create a small
   module object in sys.modules with the expected symbol(s), delegating to
   the newer functional implementation to preserve behavior.
3. Call patch_torchvision() at import time to install the shim automatically.

This ensures the rest of the application can import the legacy path without
modifying third-party library code.
"""

def patch_torchvision():
    """
    Install a minimal `torchvision.transforms.functional_tensor` module into
    sys.modules when the environment lacks it. Provides `rgb_to_grayscale`
    by delegating to `torchvision.transforms.functional.rgb_to_grayscale`.
    """
    if not hasattr(torchvision.transforms, "functional_tensor"):
        from torchvision.transforms import functional as functional_new

        module = types.ModuleType("torchvision.transforms.functional_tensor")
        module.rgb_to_grayscale = functional_new.rgb_to_grayscale
        sys.modules["torchvision.transforms.functional_tensor"] = module


patch_torchvision()