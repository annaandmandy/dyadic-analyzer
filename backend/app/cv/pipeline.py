"""Main CV pipeline that orchestrates all detection and extraction."""

import numpy as np
import cv2
from dataclasses import dataclass

from app.cv.person_detection import PersonDetector, PersonDetection
from app.cv.face_detection import FaceDetector, FaceDetection
from app.cv.pose_estimation import PoseEstimator, PoseResult
from app.cv.depth_estimation import DepthEstimator
from app.cv.gaze_estimation import GazeEstimator
from app.models.schemas import PersonFeatures, AblationConfig, DetectedPerson


@dataclass
class CVPipelineOutput:
    persons: list[PersonFeatures]
    gaze_directions: list[tuple[float, float, float]]
    gaze_intersects: tuple[bool, bool]
    mutual_gaze: bool
    depth_map: np.ndarray
    wrist_proximity: float  # min normalized distance between any wrist pair; 0 = touching


class CVPipeline:
    def __init__(self):
        self.person_detector = PersonDetector()
        self.face_detector = FaceDetector()
        self.pose_estimator = PoseEstimator()
        self.depth_estimator = DepthEstimator()
        self.gaze_estimator = GazeEstimator()

    def detect_only(self, image_rgb: np.ndarray) -> list[DetectedPerson]:
        """Run YOLO detection only (no full CV pipeline). Returns all detected persons."""
        detections = self.person_detector.detect(image_rgb, max_persons=None)
        return [
            DetectedPerson(person_id=i, bbox=d.bbox, confidence=d.confidence)
            for i, d in enumerate(detections)
        ]

    def process(
        self,
        image_rgb: np.ndarray,
        ablation: AblationConfig | None = None,
        person_indices: tuple[int, int] = (0, 1),
    ) -> CVPipelineOutput:
        """Run the full CV pipeline on an image for the selected pair of people."""
        if ablation is None:
            ablation = AblationConfig()

        h, w = image_rgb.shape[:2]

        # 0. Person detection (YOLO) — detect all, then filter to selected indices
        all_persons_yolo = self.person_detector.detect(image_rgb, max_persons=None)
        if len(all_persons_yolo) < 2:
            raise ValueError(
                f"Expected at least 2 people, YOLO detected {len(all_persons_yolo)}. "
                "Please provide an image with at least two people visible."
            )
        try:
            persons_yolo = [all_persons_yolo[i] for i in person_indices]
        except IndexError:
            raise ValueError(
                f"Selected person indices {person_indices} out of range "
                f"({len(all_persons_yolo)} people detected)."
            )

        # 1. Face detection — run per person crop for reliability on small faces
        faces = self._detect_faces_in_crops(image_rgb, persons_yolo)

        # 2. Depth estimation
        if not ablation.disable_depth:
            depth_map = self.depth_estimator.estimate(image_rgb)
        else:
            depth_map = np.ones((h, w), dtype=np.float32) * 0.5

        # 3. Pose estimation — use YOLO body bboxes directly (no expansion hack needed)
        poses = self.pose_estimator.estimate_for_body_crops(
            image_rgb, [pd.bbox for pd in persons_yolo]
        )
        while len(poses) < 2:
            poses.append(PoseEstimator._default_pose())

        # 4. Gaze estimation
        gaze_directions = []
        for face in faces:
            if not ablation.disable_gaze:
                gaze = self.gaze_estimator.estimate_gaze_direction(face)
            else:
                gaze = (0.0, 0.0, -1.0)
            gaze_directions.append(gaze)

        # 5. Gaze intersection
        if not ablation.disable_gaze:
            a_to_b, b_to_a, mutual = self.gaze_estimator.compute_mutual_gaze(
                faces[0], faces[1], gaze_directions[0], gaze_directions[1]
            )
        else:
            a_to_b, b_to_a, mutual = False, False, False

        # 6. Build PersonFeatures for each person
        persons = []
        for i, (face, pose) in enumerate(zip(faces, poses)):
            cx = (face.bbox[0] + face.bbox[2]) / 2
            cy = (face.bbox[1] + face.bbox[3]) / 2

            depth_val = self.depth_estimator.get_depth_at_bbox(depth_map, face.bbox)
            pos_3d = (cx, cy, depth_val)

            arm_span = pose.arm_span if not ablation.disable_expansion else 0.2
            shoulder_width = pose.shoulder_width if not ablation.disable_expansion else 0.15

            persons.append(PersonFeatures(
                person_id=i,
                center_2d=(cx, cy),
                depth=depth_val,
                arm_span=arm_span,
                shoulder_width=shoulder_width,
                torso_alignment=pose.torso_alignment,
                smile_probability=face.smile_probability,
                emotion_intensity=face.smile_probability,  # proxy
                face_yaw_angle=face.yaw_angle,
                face_bbox=face.bbox,
                gaze_direction=gaze_directions[i],
                position_3d=pos_3d,
            ))

        wrist_proximity = self._compute_wrist_proximity(poses)

        return CVPipelineOutput(
            persons=persons,
            gaze_directions=gaze_directions,
            gaze_intersects=(a_to_b, b_to_a),
            mutual_gaze=mutual,
            depth_map=depth_map,
            wrist_proximity=wrist_proximity,
        )

    @staticmethod
    def _compute_wrist_proximity(poses: list[PoseResult]) -> float:
        """Compute minimum distance between any wrist pair across two people.

        MediaPipe landmark indices: LEFT_WRIST=15, RIGHT_WRIST=16.
        Only considers wrists with visibility > 0.3 to avoid default-pose noise.
        Returns 1.0 if no visible wrists found.
        """
        _L_WRIST, _R_WRIST = 15, 16
        if len(poses) < 2:
            return 1.0

        def wrist(pose: PoseResult, idx: int):
            lm = pose.landmarks[idx]
            return np.array([lm[0], lm[1]]), lm[2]

        p0_lw, p0_lw_v = wrist(poses[0], _L_WRIST)
        p0_rw, p0_rw_v = wrist(poses[0], _R_WRIST)
        p1_lw, p1_lw_v = wrist(poses[1], _L_WRIST)
        p1_rw, p1_rw_v = wrist(poses[1], _R_WRIST)

        min_dist = 1.0
        for a, a_v, b, b_v in [
            (p0_lw, p0_lw_v, p1_lw, p1_lw_v),
            (p0_lw, p0_lw_v, p1_rw, p1_rw_v),
            (p0_rw, p0_rw_v, p1_lw, p1_lw_v),
            (p0_rw, p0_rw_v, p1_rw, p1_rw_v),
        ]:
            if a_v > 0.3 and b_v > 0.3:
                min_dist = min(min_dist, float(np.linalg.norm(a - b)))

        return min_dist

    def _detect_faces_in_crops(
        self, image_rgb: np.ndarray, persons: list[PersonDetection]
    ) -> list[FaceDetection]:
        """Run face detection on each YOLO person crop, re-map coords to full image.

        Falls back to an approximate face bbox from the top of the body bbox
        if FaceMesh fails on a crop (e.g. face turned away).
        """
        h, w = image_rgb.shape[:2]
        faces = []

        for pd in persons:
            x1, y1, x2, y2 = pd.bbox
            px1, py1 = int(x1 * w), int(y1 * h)
            px2, py2 = int(x2 * w), int(y2 * h)
            crop = image_rgb[py1:py2, px1:px2]
            crop_w, crop_h = px2 - px1, py2 - py1

            crop_faces = self.face_detector.detect(crop)

            if crop_faces:
                f = crop_faces[0]
                # Re-map normalized crop coords → full image normalized coords
                bx1 = (f.bbox[0] * crop_w + px1) / w
                by1 = (f.bbox[1] * crop_h + py1) / h
                bx2 = (f.bbox[2] * crop_w + px1) / w
                by2 = (f.bbox[3] * crop_h + py1) / h
                remapped_lms = {
                    k: ((lx * crop_w + px1) / w, (ly * crop_h + py1) / h)
                    for k, (lx, ly) in f.landmarks.items()
                }
                faces.append(FaceDetection(
                    bbox=(bx1, by1, bx2, by2),
                    landmarks=remapped_lms,
                    smile_probability=f.smile_probability,
                    yaw_angle=f.yaw_angle,
                ))
            else:
                # Fallback: approximate face from top 30% of YOLO body bbox
                face_y2 = y1 + (y2 - y1) * 0.3
                cx_norm = (x1 + x2) / 2
                dh = face_y2 - y1
                faces.append(FaceDetection(
                    bbox=(x1, y1, x2, face_y2),
                    landmarks={
                        "nose_tip":    (cx_norm,                    y1 + dh * 0.6),
                        "left_eye":    (x1 + 0.3 * (x2 - x1),     y1 + dh * 0.4),
                        "right_eye":   (x1 + 0.7 * (x2 - x1),     y1 + dh * 0.4),
                        "left_mouth":  (x1 + 0.35 * (x2 - x1),    y1 + dh * 0.8),
                        "right_mouth": (x1 + 0.65 * (x2 - x1),    y1 + dh * 0.8),
                    },
                    smile_probability=0.5,
                    yaw_angle=0.0,
                ))

        return faces
