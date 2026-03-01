"""Pose estimation using MediaPipe Pose."""

import numpy as np
import mediapipe as mp
from dataclasses import dataclass

from app.config import settings

# MediaPipe Pose landmark indices
_NOSE = 0
_LEFT_SHOULDER = 11
_RIGHT_SHOULDER = 12
_LEFT_ELBOW = 13
_RIGHT_ELBOW = 14
_LEFT_WRIST = 15
_RIGHT_WRIST = 16
_LEFT_HIP = 23
_RIGHT_HIP = 24


@dataclass
class PoseResult:
    landmarks: list[tuple[float, float, float]]  # (x, y, visibility)
    shoulder_width: float
    arm_span: float
    torso_alignment: float  # vertical alignment score 0-1


class PoseEstimator:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=True,
            model_complexity=settings.pose_model_complexity,
            enable_segmentation=False,
            min_detection_confidence=0.5,
        )

    def estimate(self, image_rgb: np.ndarray) -> list[PoseResult]:
        """Estimate pose for people in the image.

        MediaPipe Pose detects one person at a time, so for two people
        we crop the image based on face detections and run pose on each crop.
        """
        results = self.pose.process(image_rgb)
        if not results.pose_landmarks:
            return []

        lms = results.pose_landmarks.landmark
        landmarks = [(lm.x, lm.y, lm.visibility) for lm in lms]

        pose_result = self._extract_metrics(landmarks)
        return [pose_result]

    def estimate_for_crops(
        self, image_rgb: np.ndarray, bboxes: list[tuple[float, float, float, float]]
    ) -> list[PoseResult]:
        """Run pose estimation on cropped regions for each detected person."""
        h, w = image_rgb.shape[:2]
        results = []

        for bbox in bboxes:
            x1, y1, x2, y2 = bbox
            # Expand bbox to include full body (face bbox → estimated body region)
            cx = (x1 + x2) / 2
            face_w = x2 - x1
            face_h = y2 - y1

            # Body crop: wider and extends below face
            body_x1 = max(0, cx - face_w * 3)
            body_y1 = max(0, y1 - face_h * 0.5)
            body_x2 = min(1.0, cx + face_w * 3)
            body_y2 = min(1.0, y2 + face_h * 8)

            px1, py1 = int(body_x1 * w), int(body_y1 * h)
            px2, py2 = int(body_x2 * w), int(body_y2 * h)

            if px2 - px1 < 20 or py2 - py1 < 20:
                results.append(self._default_pose())
                continue

            crop = image_rgb[py1:py2, px1:px2]
            pose_results = self.pose.process(crop)

            if not pose_results.pose_landmarks:
                results.append(self._default_pose())
                continue

            lms = pose_results.pose_landmarks.landmark
            # Re-map landmarks from crop coords to full image coords
            crop_w = px2 - px1
            crop_h = py2 - py1
            landmarks = []
            for lm in lms:
                abs_x = (lm.x * crop_w + px1) / w
                abs_y = (lm.y * crop_h + py1) / h
                landmarks.append((abs_x, abs_y, lm.visibility))

            results.append(self._extract_metrics(landmarks))

        return results

    def _extract_metrics(self, landmarks: list[tuple[float, float, float]]) -> PoseResult:
        """Extract shoulder width, arm span, and torso alignment."""
        def lm(idx):
            return np.array(landmarks[idx][:2])

        def vis(idx):
            return landmarks[idx][2]

        # Shoulder width
        l_shoulder = lm(_LEFT_SHOULDER)
        r_shoulder = lm(_RIGHT_SHOULDER)
        shoulder_width = float(np.linalg.norm(l_shoulder - r_shoulder))

        # Arm span: left wrist to right wrist
        l_wrist = lm(_LEFT_WRIST)
        r_wrist = lm(_RIGHT_WRIST)
        arm_span = float(np.linalg.norm(l_wrist - r_wrist))

        # If wrists aren't visible, estimate from elbows
        if vis(_LEFT_WRIST) < 0.3 or vis(_RIGHT_WRIST) < 0.3:
            l_elbow = lm(_LEFT_ELBOW)
            r_elbow = lm(_RIGHT_ELBOW)
            arm_span = float(np.linalg.norm(l_elbow - r_elbow)) * 1.5

        # Torso vertical alignment (how upright is the person)
        shoulder_center = (l_shoulder + r_shoulder) / 2
        l_hip = lm(_LEFT_HIP)
        r_hip = lm(_RIGHT_HIP)
        hip_center = (l_hip + r_hip) / 2

        torso_vec = shoulder_center - hip_center
        vertical = np.array([0, -1])
        if np.linalg.norm(torso_vec) < 1e-6:
            torso_alignment = 1.0
        else:
            cos_angle = np.dot(torso_vec, vertical) / (np.linalg.norm(torso_vec) + 1e-8)
            torso_alignment = float(np.clip(cos_angle, 0, 1))

        return PoseResult(
            landmarks=landmarks,
            shoulder_width=shoulder_width,
            arm_span=arm_span,
            torso_alignment=torso_alignment,
        )

    def estimate_for_body_crops(
        self, image_rgb: np.ndarray, body_bboxes: list[tuple[float, float, float, float]]
    ) -> list[PoseResult]:
        """Run pose estimation on pre-computed full-body bounding boxes.

        Unlike estimate_for_crops (which takes face bboxes and expands them),
        this method uses body bboxes directly — as provided by YOLO.
        """
        h, w = image_rgb.shape[:2]
        results = []

        for bbox in body_bboxes:
            x1, y1, x2, y2 = bbox
            px1, py1 = int(x1 * w), int(y1 * h)
            px2, py2 = int(x2 * w), int(y2 * h)

            if px2 - px1 < 20 or py2 - py1 < 20:
                results.append(self._default_pose())
                continue

            crop = image_rgb[py1:py2, px1:px2]
            pose_result = self.pose.process(crop)

            if not pose_result.pose_landmarks:
                results.append(self._default_pose())
                continue

            lms = pose_result.pose_landmarks.landmark
            crop_w, crop_h = px2 - px1, py2 - py1
            landmarks = []
            for lm in lms:
                abs_x = (lm.x * crop_w + px1) / w
                abs_y = (lm.y * crop_h + py1) / h
                landmarks.append((abs_x, abs_y, lm.visibility))

            results.append(self._extract_metrics(landmarks))

        return results

    @staticmethod
    def _default_pose() -> PoseResult:
        return PoseResult(
            landmarks=[(0.5, 0.5, 0.0)] * 33,
            shoulder_width=0.15,
            arm_span=0.2,
            torso_alignment=0.8,
        )
