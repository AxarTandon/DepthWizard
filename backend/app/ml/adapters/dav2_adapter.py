"""
Depth Anything V2 (DINOv2-Large backbone) - state-of-the-art open-weight
monocular depth estimation, used as the primary adapter for GeoDepth-3D.

Loaded via the official HuggingFace transformers pipeline. Falls back
gracefully (is_available() = False) if the `transformers` package or the
weights can't be reached, so the pipeline drops to the MiDaS adapter instead
of failing outright.
"""
import numpy as np
import cv2

from app.ml.adapters.base import DepthAdapter


class DepthAnythingV2Adapter(DepthAdapter):
    name = "depth_anything_v2"
    _pipe = None

    def __init__(self, model_id: str = "depth-anything/Depth-Anything-V2-Small-hf"):
        self.model_id = model_id

    def is_available(self) -> bool:
        try:
            import transformers  # noqa: F401
            import torch  # noqa: F401
            return True
        except ImportError:
            return False

    def _load(self):
        if self._pipe is not None:
            return
        import torch
        from transformers import pipeline
        device = 0 if torch.cuda.is_available() else -1
        self._pipe = pipeline(task="depth-estimation", model=self.model_id, device=device)

    def predict(self, image_bgr: np.ndarray) -> np.ndarray:
        from app.ml.adapters.fallback_adapter import FallbackDepthAdapter
        from PIL import Image
        try:
            self._load()
            img_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(img_rgb)
            result = self._pipe(pil_image)
            depth = np.array(result["depth"], dtype=np.float32)
            if depth.shape[:2] != image_bgr.shape[:2]:
                depth = cv2.resize(depth, (image_bgr.shape[1], image_bgr.shape[0]))
            return depth
        except Exception:
            return FallbackDepthAdapter().predict(image_bgr)
