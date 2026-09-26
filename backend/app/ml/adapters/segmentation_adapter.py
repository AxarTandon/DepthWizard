"""
U-Net + ResNet18 (ImageNet-pretrained, free via segmentation-models-pytorch)
land-cover segmentation: background / building / water-lowland / vegetation /
road. Falls back to a color/texture heuristic when no fine-tuned checkpoint
is present, so the pipeline never breaks on a missing weights file.
"""
import os

import numpy as np
import cv2

CLASS_NAMES = ["background", "building", "water_lowland", "vegetation", "road"]
BUILDING_CLASS = 1
WATER_CLASS = 2
VEGETATION_CLASS = 3
ROAD_CLASS = 4


class SegmentationAdapter:
    _model = None
    _device = None

    def _load(self, weights_path: str):
        if self._model is not None or not weights_path or not os.path.exists(weights_path):
            return
        import torch
        import segmentation_models_pytorch as smp
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._model = smp.Unet(
            encoder_name="resnet18", encoder_weights="imagenet",
            in_channels=3, classes=len(CLASS_NAMES),
        )
        state = torch.load(weights_path, map_location=self._device, weights_only=True)
        self._model.load_state_dict(state)
        self._model.to(self._device).eval()

    def predict(self, image_bgr: np.ndarray, weights_path: str) -> np.ndarray:
        self._load(weights_path)
        if self._model is not None:
            import torch
            img_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            tensor = torch.from_numpy(img_rgb.transpose(2, 0, 1)).unsqueeze(0).to(self._device)
            with torch.no_grad():
                logits = self._model(tensor)
                mask = torch.argmax(logits, dim=1).squeeze().cpu().numpy().astype(np.uint8)
            return mask
        return self._heuristic(image_bgr)

    @staticmethod
    def _heuristic(image_bgr: np.ndarray) -> np.ndarray:
        hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
        h, w = image_bgr.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)
        veg = cv2.inRange(hsv, (35, 40, 40), (85, 255, 255))
        water = cv2.inRange(hsv, (90, 30, 40), (130, 255, 255))
        gray_mask = cv2.inRange(hsv, (0, 0, 60), (180, 40, 220))
        v = hsv[:, :, 2]
        building = cv2.bitwise_and(gray_mask, cv2.inRange(v, 140, 255))
        road = cv2.bitwise_and(gray_mask, cv2.inRange(v, 60, 140))
        mask[veg > 0] = VEGETATION_CLASS
        mask[water > 0] = WATER_CLASS
        mask[road > 0] = ROAD_CLASS
        mask[building > 0] = BUILDING_CLASS
        return mask


def get_adapter(adapter_name: str, settings):
    """Factory - returns the configured primary depth adapter, with FallbackDepthAdapter
    when running on resource-constrained environments or in demo mode."""
    from app.ml.adapters.fallback_adapter import FallbackDepthAdapter
    from app.ml.adapters.im2height_adapter import Im2HeightAdapter
    from app.ml.adapters.midas_adapter import MiDaSAdapter
    from app.ml.adapters.dav2_adapter import DepthAnythingV2Adapter

    # In DEMO_MODE (default for free-tier cloud deployments with 512MB RAM),
    # use the instant OpenCV topographic elevation adapter to avoid downloading
    # 1.5GB neural network weights and getting OOM-killed.
    if getattr(settings, "DEMO_MODE", False) or adapter_name == "fallback":
        return FallbackDepthAdapter()

    if adapter_name == "dav2":
        adapter = DepthAnythingV2Adapter()
        if adapter.is_available():
            return adapter
    if adapter_name == "im2height":
        adapter = Im2HeightAdapter(settings.IM2HEIGHT_WEIGHTS_PATH)
        if adapter.is_available():
            return adapter
    midas = MiDaSAdapter(settings.MIDAS_MODEL_TYPE)
    if midas.is_available():
        return midas
    return FallbackDepthAdapter()
