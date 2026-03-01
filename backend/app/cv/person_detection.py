"""Person detection using YOLOv8 (Ultralytics)."""

import numpy as np
from dataclasses import dataclass

from app.config import settings


@dataclass
class PersonDetection:
    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2 normalized [0, 1]
    confidence: float


class PersonDetector:
    def __init__(self):
        from ultralytics import YOLO
        self.model = YOLO(settings.yolo_model)
        self.conf = settings.yolo_conf
        self.imgsz = settings.yolo_imgsz

    def detect(self, image_rgb: np.ndarray) -> list[PersonDetection]:
        """Detect persons in image, return up to 2 sorted left-to-right.

        Uses class 0 (person) only. Top-2 by confidence are kept, then
        sorted left-to-right for consistent person_id assignment.
        """
        h, w = image_rgb.shape[:2]
        results = self.model.predict(
            image_rgb,
            imgsz=self.imgsz,
            conf=self.conf,
            classes=[0],
            verbose=False,
        )

        detections = []
        for box in results[0].boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            detections.append(PersonDetection(
                bbox=(x1 / w, y1 / h, x2 / w, y2 / h),
                confidence=float(box.conf[0]),
            ))

        # Keep top-2 by confidence, then sort left-to-right
        detections.sort(key=lambda d: d.confidence, reverse=True)
        detections = detections[:2]
        detections.sort(key=lambda d: d.bbox[0])
        return detections
