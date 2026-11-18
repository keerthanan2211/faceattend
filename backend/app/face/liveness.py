"""
Active liveness with a random head-turn challenge, verified on the server.

The kiosk captures one frame looking straight and one after the person turns their head
in a direction the SERVER chose at random. A printed photo can't turn, and a pre-recorded
video can't know which way it will be asked to turn.

Yaw is estimated from 5 landmarks: how far the nose tip sits from the midpoint between the eyes,
relative to the distance between the eyes. Turning to your LEFT moves your nose toward the
right side of an (un-mirrored) camera image, giving a positive value.
"""

from dataclasses import dataclass
from typing import Literal

import numpy as np

Direction = Literal["left", "right"]


def yaw_ratio(landmarks: np.ndarray) -> float:
    right_eye, left_eye, nose = landmarks[0], landmarks[1], landmarks[2]
    eye_mid_x = (right_eye[0] + left_eye[0]) / 2
    inter_eye = float(np.linalg.norm(left_eye - right_eye))
    if inter_eye < 1e-6:
        raise ValueError("Eyes not detected clearly")
    return float((nose[0] - eye_mid_x) / inter_eye)


@dataclass(frozen=True)
class LivenessResult:
    passed: bool
    reason: str  # "ok" | "not-straight" | "no-turn" | "wrong-direction" | "different-person"
    straight_yaw: float
    turned_yaw: float
    continuity: float


def check_head_turn(
    straight: np.ndarray,
    turned: np.ndarray,
    direction: Direction,
    continuity: float,
    *,
    straight_max: float,
    turn_min: float,
    continuity_min: float,
) -> LivenessResult:
    s, t = yaw_ratio(straight), yaw_ratio(turned)
    expected_sign = 1 if direction == "left" else -1

    def result(passed: bool, reason: str) -> LivenessResult:
        return LivenessResult(passed, reason, round(s, 3), round(t, 3), round(continuity, 3))

    # Both frames must show the same person, so someone can't swap faces between the two captures
    if continuity < continuity_min:
        return result(False, "different-person")
    if abs(s) > straight_max:
        return result(False, "not-straight")
    if t * expected_sign < turn_min:
        return result(False, "wrong-direction" if t * expected_sign <= -turn_min else "no-turn")
    return result(True, "ok")


MESSAGES = {
    "not-straight": "Start by looking straight at the camera, then turn when asked.",
    "no-turn": "We didn't see your head turn. Turn a little further when asked.",
    "wrong-direction": "You turned the other way. Follow the arrow on screen.",
    "different-person": "The two photos didn't match. Stay in front of the camera for the whole scan.",
}
