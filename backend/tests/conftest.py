import io
import os
import tempfile

import numpy as np
import pytest
from PIL import Image

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"
os.environ["ADMIN_API_KEY"] = "test-admin-key"
os.environ["TEMPLATE_KEY"] = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="  # 32 test bytes
os.environ["MATCH_THRESHOLD"] = "0.90"
os.environ["MATCH_MARGIN"] = "0.02"
os.environ["CONTINUITY_THRESHOLD"] = "0.90"

from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine, init_db  # noqa: E402
from app.face.engine import FaceAnalysis, FaceError, get_engine, normalise  # noqa: E402
from app.main import create_app  # noqa: E402

ADMIN = {"X-Admin-Key": "test-admin-key"}


class FakeEngine:
    """Stands in for YuNet + SFace. Each image's average colour per quadrant becomes the 'embedding'
    (different colours = different people), and a small marker in the top-left corner sets the head
    yaw, so tests can simulate looking straight or turning. A black image means "no face"."""

    def analyze(self, image: np.ndarray) -> FaceAnalysis:
        if image.mean() < 5:
            raise FaceError("No face found. Face the camera in good light and try again.")
        h, w, _ = image.shape
        quads = [
            image[: h // 2, : w // 2],
            image[: h // 2, w // 2 :],
            image[h // 2 :, : w // 2],
            image[h // 2 :, w // 2 :],
        ]
        embedding = normalise(np.concatenate([q.reshape(-1, 3).mean(axis=0) for q in quads]) - 100)
        yaw = (float(image[:MARK, :MARK, 2].mean()) - 128) / 200
        # Eyes 60 px apart; the nose sits off-centre by yaw * eye distance
        landmarks = np.array([[70, 80], [130, 80], [100 + yaw * 60, 110], [80, 140], [120, 140]], dtype=float)
        return FaceAnalysis(embedding, landmarks, 0.99)


MARK = 6


def photo(rgb: tuple[int, int, int], yaw: float = 0.0) -> bytes:
    """A lossless test 'face'. yaw > 0 means turned to the person's left."""
    img = Image.new("RGB", (200, 200), rgb)
    arr = np.array(img)
    arr[:MARK, :MARK, 2] = int(128 + yaw * 200)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, "PNG")
    return buf.getvalue()


# Two clearly different "people", plus a second photo of person A in slightly different light
PERSON_A = (220, 60, 60)
PERSON_A_2 = (200, 80, 60)
PERSON_B = (40, 200, 90)


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    init_db()
    app = create_app()
    app.dependency_overrides[get_engine] = lambda: FakeEngine()
    app.state.limiter.enabled = False
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def tech(client):
    def create(code: str, name: str, *photos: bytes) -> dict:
        res = client.post(
            "/api/technicians",
            headers=ADMIN,
            json={"employee_code": code, "name": name, "trade": "Electrician", "phone": "9876543210"},
        )
        assert res.status_code == 201, res.text
        t = res.json()
        if photos:
            files = [("files", (f"{i}.png", p, "image/png")) for i, p in enumerate(photos)]
            res = client.post(f"/api/technicians/{t['id']}/faces", headers=ADMIN, files=files)
            assert res.status_code == 200, res.text
            t = res.json()
        return t

    return create
