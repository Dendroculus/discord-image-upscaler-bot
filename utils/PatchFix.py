import sys
import types
import torchvision

"""
PatchFix.py

Compatibility shim that ensures older code expecting
`torchvision.transforms.functional_tensor` finds required attributes.

Call `patch_torchvision()` early in application startup to install the shim.
"""


def patch_torchvision():
    """
    Install a minimal `torchvision.transforms.functional_tensor` module into
    sys.modules when the environment lacks it. This provides `rgb_to_grayscale`
    by delegating to the new functional implementation when necessary.
    """
    if not hasattr(torchvision.transforms, "functional_tensor"):
        from torchvision.transforms import functional as functional_new

        module = types.ModuleType("torchvision.transforms.functional_tensor")
        module.rgb_to_grayscale = functional_new.rgb_to_grayscale
        sys.modules["torchvision.transforms.functional_tensor"] = module


patch_torchvision()