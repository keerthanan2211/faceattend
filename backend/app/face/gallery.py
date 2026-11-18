from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crypto import get_cipher
from app.models import FaceTemplate, Technician


def load_gallery(
    db: Session, exclude_technician: int | None = None, active_only: bool = True
) -> list[tuple[int, list[float]]]:
    """Decrypts enrolled templates as (technician_id, embedding) pairs for matching."""
    q = select(FaceTemplate.technician_id, FaceTemplate.ciphertext).join(Technician)
    if active_only:
        q = q.where(Technician.active.is_(True))
    if exclude_technician is not None:
        q = q.where(FaceTemplate.technician_id != exclude_technician)
    cipher = get_cipher()
    return [(tid, cipher.decrypt(blob)) for tid, blob in db.execute(q).all()]
