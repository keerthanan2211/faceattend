from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.crypto import get_cipher
from app.db import get_db
from app.face.engine import FaceEngine, FaceError, get_engine
from app.face.gallery import load_gallery
from app.face.matching import is_duplicate_enrolment, match
from app.models import FaceTemplate, Technician
from app.schemas import TechnicianIn, TechnicianOut, TechnicianUpdate
from app.security import require_admin
from app.services.images import ImageError, load_rgb

router = APIRouter(prefix="/technicians", tags=["technicians"], dependencies=[Depends(require_admin)])


def _out(t: Technician, face_count: int) -> TechnicianOut:
    return TechnicianOut.model_validate(t).model_copy(update={"face_count": face_count})


def _get(db: Session, tech_id: int) -> Technician:
    tech = db.get(Technician, tech_id)
    if tech is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Technician not found")
    return tech


@router.get("", response_model=list[TechnicianOut])
def list_technicians(db: Session = Depends(get_db)):
    counts = dict(
        db.execute(select(FaceTemplate.technician_id, func.count()).group_by(FaceTemplate.technician_id)).all()
    )
    techs = db.scalars(select(Technician).order_by(Technician.name)).all()
    return [_out(t, counts.get(t.id, 0)) for t in techs]


@router.post("", response_model=TechnicianOut, status_code=status.HTTP_201_CREATED)
def create_technician(body: TechnicianIn, db: Session = Depends(get_db)):
    tech = Technician(**body.model_dump() | {"employee_code": body.employee_code.upper()})
    db.add(tech)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "That employee code is already registered") from exc
    return _out(tech, 0)


@router.patch("/{tech_id}", response_model=TechnicianOut)
def update_technician(tech_id: int, body: TechnicianUpdate, db: Session = Depends(get_db)):
    tech = _get(db, tech_id)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(tech, key, value)
    db.commit()
    return _out(tech, len(tech.faces))


@router.delete("/{tech_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_technician(tech_id: int, db: Session = Depends(get_db)):
    db.delete(_get(db, tech_id))
    db.commit()


@router.post("/{tech_id}/faces", response_model=TechnicianOut)
async def enroll_faces(
    tech_id: int,
    files: list[UploadFile] = File(..., description="1 to 3 clear photos of the technician's face"),
    db: Session = Depends(get_db),
    engine: FaceEngine = Depends(get_engine),
):
    """Enrols face photos. Only encrypted embeddings are stored; the photos are discarded."""
    settings = get_settings()
    tech = _get(db, tech_id)
    if not 1 <= len(files) <= 3:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Upload between 1 and 3 photos")
    if len(tech.faces) + len(files) > settings.max_faces_per_person:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"A technician can have at most {settings.max_faces_per_person} face photos"
        )

    # Compare against everyone else, active or not, so a face can't be enrolled under two names
    others = load_gallery(db, exclude_technician=tech_id, active_only=False)
    cipher = get_cipher()
    existing = [cipher.decrypt(f.ciphertext) for f in tech.faces]
    new_vectors: list[list[float]] = []

    for i, upload in enumerate(files, start=1):
        try:
            vector = engine.analyze(load_rgb(await upload.read(), settings.max_image_mb)).embedding
        except (ImageError, FaceError) as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Photo {i}: {exc}") from exc

        # Refuse a face that already confidently matches SOMEONE ELSE (prevents enrolling the wrong person)
        clash = match(vector, others, settings.match_threshold, 0.0)
        if clash.person_id is not None:
            other = db.get(Technician, clash.person_id)
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Photo {i} matches {other.name} ({other.employee_code}), who is already enrolled",
            )
        if is_duplicate_enrolment(vector, existing + new_vectors):
            raise HTTPException(status.HTTP_409_CONFLICT, f"Photo {i} is a duplicate of a photo already enrolled")
        new_vectors.append(vector)

    db.add_all(FaceTemplate(technician_id=tech.id, ciphertext=cipher.encrypt(v)) for v in new_vectors)
    db.commit()
    db.refresh(tech)
    return _out(tech, len(tech.faces))


@router.delete("/{tech_id}/faces", response_model=TechnicianOut)
def reset_faces(tech_id: int, db: Session = Depends(get_db)):
    tech = _get(db, tech_id)
    tech.faces.clear()
    db.commit()
    return _out(tech, 0)
