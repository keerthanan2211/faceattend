import numpy as np

from app.face.engine import normalise
from app.face.matching import best_scores, is_duplicate_enrolment, match

A = normalise([1.0, 0.0, 0.0])
A2 = normalise([0.95, 0.1, 0.0])
B = normalise([0.0, 1.0, 0.0])
NEAR_A = normalise([0.9, 0.2, 0.0])


def test_best_score_uses_each_persons_closest_template():
    scores = best_scores(A, [(1, B), (1, A2), (2, B)])
    assert scores[1] > 0.99 and scores[2] == 0.0


def test_accepts_a_clear_match():
    result = match(A, [(1, A2), (2, B)], threshold=0.8, margin=0.05)
    assert (result.person_id, result.reason) == (1, "match")


def test_rejects_low_similarity():
    result = match(normalise([0.0, 0.0, 1.0]), [(1, A), (2, B)], threshold=0.8, margin=0.05)
    assert (result.person_id, result.reason) == (None, "below-threshold")


def test_rejects_when_two_people_are_too_similar():
    result = match(A, [(1, A2), (2, NEAR_A)], threshold=0.8, margin=0.2)
    assert (result.person_id, result.reason) == (None, "ambiguous")


def test_handles_no_enrolled_faces():
    assert match(A, [], 0.8, 0.05).reason == "no-enrolled-faces"


def test_detects_duplicate_enrolment():
    assert is_duplicate_enrolment(A, [B, A])
    assert not is_duplicate_enrolment(A, [A2])


def test_normalise_produces_unit_vectors():
    assert np.isclose(np.linalg.norm(normalise([3, 4])), 1.0)
