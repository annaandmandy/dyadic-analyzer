"""Monocular depth estimation using MiDaS."""

import numpy as np
import cv2
import torch
from app.config import settings


class DepthEstimator:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.transform = None

    def _load_model(self):
        """Lazy-load MiDaS model on first use."""
        if self.model is not None:
            return

        self.model = torch.hub.load("intel-isl/MiDaS", settings.midas_model_type)
        self.model.to(self.device)
        self.model.eval()

        midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
        if settings.midas_model_type == "MiDaS_small":
            self.transform = midas_transforms.small_transform
        else:
            self.transform = midas_transforms.dpt_transform

    def estimate(self, image_rgb: np.ndarray) -> np.ndarray:
        """Return a depth map (H, W) with relative depth values."""
        self._load_model()

        input_batch = self.transform(image_rgb).to(self.device)

        with torch.no_grad():
            prediction = self.model(input_batch)
            prediction = torch.nn.functional.interpolate(
                prediction.unsqueeze(1),
                size=image_rgb.shape[:2],
                mode="bicubic",
                align_corners=False,
            ).squeeze()

        depth_map = prediction.cpu().numpy()

        # Normalize to 0-1 range (higher = closer)
        d_min, d_max = depth_map.min(), depth_map.max()
        if d_max - d_min > 1e-6:
            depth_map = (depth_map - d_min) / (d_max - d_min)
        else:
            depth_map = np.ones_like(depth_map) * 0.5

        return depth_map

    def get_depth_at_bbox(
        self, depth_map: np.ndarray, bbox: tuple[float, float, float, float]
    ) -> float:
        """Get median depth inside a bounding box (normalized coords)."""
        h, w = depth_map.shape[:2]
        x1, y1, x2, y2 = bbox
        px1, py1 = int(x1 * w), int(y1 * h)
        px2, py2 = int(x2 * w), int(y2 * h)

        px1 = max(0, min(px1, w - 1))
        px2 = max(0, min(px2, w - 1))
        py1 = max(0, min(py1, h - 1))
        py2 = max(0, min(py2, h - 1))

        if px2 <= px1 or py2 <= py1:
            return 0.5

        region = depth_map[py1:py2, px1:px2]
        return float(np.median(region))
