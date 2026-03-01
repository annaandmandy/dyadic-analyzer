"""Face detection using MediaPipe or RetinaFace."""

import numpy as np
import cv2
import mediapipe as mp
from dataclasses import dataclass

from app.config import settings


@dataclass
class FaceDetection:
    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2 normalized
    landmarks: dict[str, tuple[float, float]]  # key facial landmarks
    smile_probability: float
    yaw_angle: float  # estimated from landmarks


class FaceDetector:
    def __init__(self):
        self.backend = settings.face_detection_backend
        if self.backend == "mediapipe":
            self._init_mediapipe()
        else:
            self._init_retinaface()

    def _init_mediapipe(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=2,
            refine_landmarks=True,
            min_detection_confidence=0.5,
        )

    def _init_retinaface(self):
        try:
            from retinaface import RetinaFace as RF
            self._retinaface = RF
        except ImportError:
            raise ImportError("retinaface package required. Install: pip install retina-face")

    def detect(self, image_rgb: np.ndarray) -> list[FaceDetection]:
        if self.backend == "mediapipe":
            return self._detect_mediapipe(image_rgb)
        return self._detect_retinaface(image_rgb)

    def _detect_mediapipe(self, image_rgb: np.ndarray) -> list[FaceDetection]:
        h, w = image_rgb.shape[:2]
        results = self.face_mesh.process(image_rgb)
        if not results.multi_face_landmarks:
            return []

        detections = []
        for face_landmarks in results.multi_face_landmarks:
            lms = face_landmarks.landmark

            # Extract key landmarks (MediaPipe face mesh indices)
            xs = [lm.x for lm in lms]
            ys = [lm.y for lm in lms]
            x1, x2 = min(xs), max(xs)
            y1, y2 = min(ys), max(ys)

            # Key landmark positions
            landmarks = {
                "nose_tip": (lms[1].x, lms[1].y),
                "left_eye": (lms[33].x, lms[33].y),
                "right_eye": (lms[263].x, lms[263].y),
                "left_mouth": (lms[61].x, lms[61].y),
                "right_mouth": (lms[291].x, lms[291].y),
                "chin": (lms[199].x, lms[199].y),
                "forehead": (lms[10].x, lms[10].y),
                "left_ear": (lms[234].x, lms[234].y),
                "right_ear": (lms[454].x, lms[454].y),
            }

            # Estimate smile probability from mouth shape
            smile_prob = self._estimate_smile(lms)

            # Estimate yaw from landmark asymmetry
            yaw = self._estimate_yaw(landmarks)

            detections.append(FaceDetection(
                bbox=(x1, y1, x2, y2),
                landmarks=landmarks,
                smile_probability=smile_prob,
                yaw_angle=yaw,
            ))

        return detections[:2]  # Max 2 people

    def _detect_retinaface(self, image_rgb: np.ndarray) -> list[FaceDetection]:
        h, w = image_rgb.shape[:2]
        image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
        faces = self._retinaface.detect_faces(image_bgr)

        if not isinstance(faces, dict):
            return []

        detections = []
        for key, face_data in faces.items():
            area = face_data["facial_area"]
            x1, y1, x2, y2 = area[0] / w, area[1] / h, area[2] / w, area[3] / h

            raw_lms = face_data.get("landmarks", {})
            landmarks = {}
            for name, (px, py) in raw_lms.items():
                landmarks[name] = (px / w, py / h)

            # Map RetinaFace landmark names
            mapped = {
                "nose_tip": landmarks.get("nose", ((x1 + x2) / 2, (y1 + y2) / 2)),
                "left_eye": landmarks.get("left_eye", (x1 + 0.3 * (x2 - x1), y1 + 0.35 * (y2 - y1))),
                "right_eye": landmarks.get("right_eye", (x1 + 0.7 * (x2 - x1), y1 + 0.35 * (y2 - y1))),
                "left_mouth": landmarks.get("mouth_left", (x1 + 0.35 * (x2 - x1), y1 + 0.75 * (y2 - y1))),
                "right_mouth": landmarks.get("mouth_right", (x1 + 0.65 * (x2 - x1), y1 + 0.75 * (y2 - y1))),
            }

            smile_prob = face_data.get("score", 0.5)
            yaw = self._estimate_yaw(mapped)

            detections.append(FaceDetection(
                bbox=(x1, y1, x2, y2),
                landmarks=mapped,
                smile_probability=smile_prob,
                yaw_angle=yaw,
            ))

        # Sort by x-position (left to right), return max 2
        detections.sort(key=lambda d: d.bbox[0])
        return detections[:2]

    @staticmethod
    def _estimate_smile(landmarks) -> float:
        """Estimate smile probability from mouth landmark geometry."""
        # Mouth corners (61, 291) and upper/lower lips (13, 14)
        left_mouth = np.array([landmarks[61].x, landmarks[61].y])
        right_mouth = np.array([landmarks[291].x, landmarks[291].y])
        upper_lip = np.array([landmarks[13].x, landmarks[13].y])
        lower_lip = np.array([landmarks[14].x, landmarks[14].y])

        mouth_width = np.linalg.norm(right_mouth - left_mouth)
        mouth_height = np.linalg.norm(lower_lip - upper_lip)

        if mouth_width < 1e-6:
            return 0.0

        ratio = mouth_height / mouth_width
        # Smile tends to widen the mouth — higher width-to-height ratio
        # Typical smile ratio is around 0.15-0.3
        smile_score = np.clip(1.0 - ratio * 3.0, 0.0, 1.0)
        return float(smile_score)

    @staticmethod
    def _estimate_yaw(landmarks: dict) -> float:
        """Estimate face yaw angle from landmark asymmetry."""
        nose = np.array(landmarks.get("nose_tip", (0.5, 0.5)))
        left_eye = np.array(landmarks.get("left_eye", (0.3, 0.4)))
        right_eye = np.array(landmarks.get("right_eye", (0.7, 0.4)))

        eye_center = (left_eye + right_eye) / 2.0
        left_dist = np.linalg.norm(nose - left_eye)
        right_dist = np.linalg.norm(nose - right_eye)

        total = left_dist + right_dist
        if total < 1e-6:
            return 0.0

        # Asymmetry ratio: positive = facing right, negative = facing left
        asymmetry = (left_dist - right_dist) / total
        yaw_degrees = asymmetry * 90.0  # rough mapping
        return float(np.clip(yaw_degrees, -90, 90))
