import numpy as np
import pytest

from app.face.liveness import check_head_turn, yaw_ratio


def face(yaw: float) -> np.ndarray:
    return np.array([[70, 80], [130, 80], [100 + yaw * 60, 110], [80, 140], [120, 140]], dtype=float)


LIMITS = dict(straight_max=0.12, turn_min=0.20, continuity_min=0.30)


def test_yaw_ratio_measures_nose_offset():
    assert yaw_ratio(face(0)) == 0
    assert yaw_ratio(face(0.3)) == pytest.approx(0.3)
    assert yaw_ratio(face(-0.25)) == pytest.approx(-0.25)


@pytest.mark.parametrize("direction, turned", [("left", 0.3), ("right", -0.3)])
def test_passes_when_turning_as_asked(direction, turned):
    assert check_head_turn(face(0.02), face(turned), direction, 0.8, **LIMITS).passed


def test_rejects_a_static_photo():
    assert check_head_turn(face(0), face(0.05), "left", 0.99, **LIMITS).reason == "no-turn"


def test_rejects_the_wrong_direction():
    assert check_head_turn(face(0), face(-0.3), "left", 0.8, **LIMITS).reason == "wrong-direction"


def test_requires_looking_straight_first():
    assert check_head_turn(face(0.25), face(0.4), "left", 0.8, **LIMITS).reason == "not-straight"


def test_rejects_a_different_person_in_the_second_frame():
    assert check_head_turn(face(0), face(0.3), "left", 0.1, **LIMITS).reason == "different-person"
