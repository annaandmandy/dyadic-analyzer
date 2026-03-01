"""Gaze direction estimation from face landmarks."""

import numpy as np
from app.cv.face_detection import FaceDetection


class GazeEstimator:
    def estimate_gaze_direction(self, face: FaceDetection) -> tuple[float, float, float]:
        """Estimate a 3D gaze direction vector from facial landmarks.

        Uses the face yaw angle and the eye-to-nose vector as a proxy
        for gaze direction. Returns a normalized (dx, dy, dz) vector.
        """
        nose = np.array(face.landmarks.get("nose_tip", (0.5, 0.5)))
        left_eye = np.array(face.landmarks.get("left_eye", (0.35, 0.4)))
        right_eye = np.array(face.landmarks.get("right_eye", (0.65, 0.4)))

        eye_center = (left_eye + right_eye) / 2.0

        # 2D gaze direction: from eye center toward where nose points
        gaze_2d = nose - eye_center

        # Convert yaw to a lateral component
        yaw_rad = np.radians(face.yaw_angle)

        # Construct 3D direction vector
        dx = float(np.sin(yaw_rad))  # lateral (positive = right)
        dy = float(gaze_2d[1])  # vertical component
        dz = float(-np.cos(yaw_rad))  # depth (negative = into screen)

        # Normalize
        magnitude = np.sqrt(dx**2 + dy**2 + dz**2)
        if magnitude < 1e-6:
            return (0.0, 0.0, -1.0)

        return (dx / magnitude, dy / magnitude, dz / magnitude)

    def check_gaze_intersection(
        self,
        gaze_origin: tuple[float, float],
        gaze_direction: tuple[float, float, float],
        target_bbox: tuple[float, float, float, float],
        tolerance: float = 0.15,
    ) -> bool:
        """Check if a gaze ray approximately intersects another person's bbox.

        Projects the gaze direction onto the 2D image plane and checks
        if the ray passes through or near the target bounding box.
        """
        ox, oy = gaze_origin
        dx, dy, dz = gaze_direction

        tx1, ty1, tx2, ty2 = target_bbox

        # Expand target bbox by tolerance
        tx1 -= tolerance
        ty1 -= tolerance
        tx2 += tolerance
        ty2 += tolerance

        # Project gaze as a 2D ray: origin + t * (dx, dy)
        # Check if there exists t > 0 such that ray hits bbox
        if abs(dx) < 1e-6 and abs(dy) < 1e-6:
            # Gaze is straight into/out of screen — check if origin is in bbox
            return tx1 <= ox <= tx2 and ty1 <= oy <= ty2

        # Sample along the ray
        for t in np.linspace(0.01, 2.0, 50):
            px = ox + t * dx
            py = oy + t * dy
            if tx1 <= px <= tx2 and ty1 <= py <= ty2:
                return True

        return False

    def compute_mutual_gaze(
        self,
        face_a: FaceDetection,
        face_b: FaceDetection,
        gaze_a: tuple[float, float, float],
        gaze_b: tuple[float, float, float],
    ) -> tuple[bool, bool, bool]:
        """Compute gaze intersection for both directions and mutual gaze.

        Returns: (a_looks_at_b, b_looks_at_a, mutual_gaze)
        """
        center_a = ((face_a.bbox[0] + face_a.bbox[2]) / 2, (face_a.bbox[1] + face_a.bbox[3]) / 2)
        center_b = ((face_b.bbox[0] + face_b.bbox[2]) / 2, (face_b.bbox[1] + face_b.bbox[3]) / 2)

        a_looks_at_b = self.check_gaze_intersection(center_a, gaze_a, face_b.bbox)
        b_looks_at_a = self.check_gaze_intersection(center_b, gaze_b, face_a.bbox)
        mutual = a_looks_at_b and b_looks_at_a

        return a_looks_at_b, b_looks_at_a, mutual
