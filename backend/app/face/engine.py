"""
Face engine: finds exactly one face, returns its 5 landmarks and a 128-number embedding.

Production uses two small open-source ONNX models run by OpenCV:
  - YuNet (face detection + eyes, nose and mouth-corner landmarks)
  - SFace (face recognition embeddings)
The app depends only on the `FaceEngine` interface; tests use a fake engine.
"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Protocol

import numpy as np

from app.config import get_settings

DETECTOR_FILE = "face_detection_yunet_2023mar.onnx"
RECOGNIZER_FILE = "face_recognition_sface_2021dec.onnx"


class FaceError(ValueError):
    """The image can't be used: no face, several faces, or a face that's too small."""


class EngineUnavailable(RuntimeError):
    """OpenCV or the model files aren't available."""


@dataclass(frozen=True)
class FaceAnalysis:
    embedding: list[float]  # L2-normalised
    landmarks: np.ndarray  # 5x2: right eye, left eye, nose tip, right mouth corner, left mouth corner (image coords)
    score: float  # detector confidence


class FaceEngine(Protocol):
    def analyze(self, image: np.ndarray) -> FaceAnalysis: ...


def normalise(vector) -> list[float]:
    v = np.asarray(vector, dtype=np.float64).ravel()
    norm = np.linalg.norm(v)
    if norm == 0:
        raise FaceError("Couldn't read facial features from this image")
    return (v / norm).tolist()


class OpenCVEngine:
    MIN_FACE_PX = 80
    MIN_SCORE = 0.85

    def __init__(self, models_dir: str):
        try:
            import cv2
        except ImportError as exc:
            raise EngineUnavailable("OpenCV isn't installed. Run: pip install -r requirements.txt") from exc

        root = Path(models_dir)
        det, rec = root / DETECTOR_FILE, root / RECOGNIZER_FILE
        if not det.exists() or not rec.exists():
            raise EngineUnavailable("Face models are missing. Run: python scripts/download_models.py")

        self._cv2 = cv2
        self._detector = cv2.FaceDetectorYN.create(str(det), "", (320, 320), self.MIN_SCORE, 0.3, 5)
        self._recognizer = cv2.FaceRecognizerSF.create(str(rec), "")

    def analyze(self, image: np.ndarray) -> FaceAnalysis:
        bgr = np.ascontiguousarray(image[:, :, ::-1])
        h, w = bgr.shape[:2]
        self._detector.setInputSize((w, h))
        _, faces = self._detector.detect(bgr)

        if faces is None or len(faces) == 0:
            raise FaceError("No face found. Face the camera in good light and try again.")
        if len(faces) > 1:
            raise FaceError("More than one face is in view. Only one person should be in the frame.")
        face = faces[0]
        if min(face[2], face[3]) < self.MIN_FACE_PX:
            raise FaceError("Your face is too far from the camera. Move closer and try again.")

        aligned = self._recognizer.alignCrop(bgr, face)  # rotates and crops using the eye landmarks
        embedding = self._recognizer.feature(aligned)
        return FaceAnalysis(normalise(embedding), face[4:14].reshape(5, 2).astype(np.float64), float(face[14]))


@lru_cache
def get_engine() -> FaceEngine:
    return OpenCVEngine(get_settings().models_dir)
