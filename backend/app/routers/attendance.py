import base64
import csv
import hashlib
import hmac
import io
from datetime import UTC, date, datetime, time, timedelta

import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.crypto import get_cipher
from app.db import get_db
from app.face import challenge
from app.face.engine import FaceEngine, FaceError, get_engine
from app.face.gallery import load_gallery
from app.face.liveness import MESSAGES as LIVENESS_MESSAGES
from app.face.liveness import check_head_turn
from app.face.matching import best_scores, match
from app.limiter import limiter
from app.models import AttendanceRecord, FailedAttempt, Technician, UsedChallenge
from app.schemas import AttendanceOut, ChallengeOut, CheckInOut, TechnicianOut
from app.security import require_admin
from app.services.images import ImageError, load_rgb

router = APIRouter(prefix="/attendance", tags=["attendance"])

REJECTION = {
    "no-enrolled-faces": "No one is enrolled yet. Ask an admin to enrol technicians first.",
    "below-threshold": "Face not recognised. Make sure you're enrolled, then try again facing the camera.",
    "ambiguous": "Couldn't tell who this is with confidence. Remove glasses or hats and try again.",
}


def _as_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)  # SQLite returns naive datetimes


def _challenge_secret() -> bytes:
    # Derived from the template key, so there's one secret to manage
    return hmac.new(base64.b64decode(get_settings().template_key), b"liveness-challenge", hashlib.sha256).digest()


@router.get("/challenge", response_model=ChallengeOut)
@limiter.limit("30/minute")
def new_challenge(request: Request):
    """Step 1 of a scan: the server picks a random head-turn direction for this attempt."""
    get_cipher()  # fail early with a clear message if TEMPLATE_KEY isn't configured
    token, direction, expires = challenge.issue(_challenge_secret(), get_settings().challenge_ttl_seconds)
    return ChallengeOut(token=token, direction=direction, expires_at=datetime.fromtimestamp(expires, UTC))


@router.post("/check-in", response_model=CheckInOut)
@limiter.limit("30/minute")
async def check_in(
    request: Request,
    straight: UploadFile = File(..., description="Frame looking straight at the camera"),
    turned: UploadFile = File(..., description="Frame after turning the head as challenged"),
    token: str = Form(...),
    site: str = Form(..., min_length=2, max_length=80),
    db: Session = Depends(get_db),
    engine: FaceEngine = Depends(get_engine),
):
    """
    Step 2: verify the challenge, run liveness on both frames, then identify the person.
    A scan is accepted only if ALL of these pass:
      1. the challenge token is genuine, unexpired and unused
      2. both frames show the same person (continuity)
      3. the head was straight, then turned the challenged way (liveness)
      4. both frames identify the same enrolled technician (multi-frame consensus)
    """
    settings = get_settings()

    try:
        nonce, direction = challenge.verify(_challenge_secret(), token)
    except challenge.ChallengeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    if db.get(UsedChallenge, nonce):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This scan was already submitted. Start again.")
    _expire_old_challenges(db)
    db.add(UsedChallenge(nonce=nonce, expires_at=datetime.now(UTC) + timedelta(seconds=settings.challenge_ttl_seconds)))
    db.commit()

    try:
        front = engine.analyze(load_rgb(await straight.read(), settings.max_image_mb))
        side = engine.analyze(load_rgb(await turned.read(), settings.max_image_mb))
    except (ImageError, FaceError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    continuity = float(np.dot(front.embedding, side.embedding))
    live = check_head_turn(
        front.landmarks,
        side.landmarks,
        direction,
        continuity,
        straight_max=settings.straight_max_yaw,
        turn_min=settings.turn_min_yaw,
        continuity_min=settings.continuity_threshold,
    )
    if not live.passed:
        _log_failure(db, site, f"liveness:{live.reason}", None)
        raise HTTPException(status.HTTP_403_FORBIDDEN, LIVENESS_MESSAGES[live.reason])

    gallery = load_gallery(db)
    primary = match(front.embedding, gallery, settings.match_threshold, settings.match_margin)
    if primary.person_id is None:
        _log_failure(db, site, primary.reason, primary.score)
        raise HTTPException(status.HTTP_404_NOT_FOUND, REJECTION[primary.reason])

    # Consensus: the turned frame must point to the same person. A turned face scores lower,
    # so it only needs to be that person's closest match, not clear the full threshold.
    second = best_scores(side.embedding, gallery)
    if max(second, key=second.get) != primary.person_id:
        _log_failure(db, site, "no-consensus", primary.score)
        raise HTTPException(status.HTTP_404_NOT_FOUND, REJECTION["ambiguous"])

    tech = db.get(Technician, primary.person_id)
    now = datetime.now(UTC)
    last = db.scalars(
        select(AttendanceRecord)
        .where(AttendanceRecord.technician_id == tech.id)
        .order_by(AttendanceRecord.created_at.desc())
    ).first()
    out = TechnicianOut.model_validate(tech).model_copy(update={"face_count": len(tech.faces)})

    # Debounce: a second scan right after the first shouldn't flip check-in into check-out
    if last and now - _as_utc(last.created_at) < timedelta(seconds=settings.debounce_seconds):
        return CheckInOut(status="already-recorded", technician=out, time=_as_utc(last.created_at), score=primary.score)

    checked_in_today = last is not None and last.kind == "in" and _as_utc(last.created_at).date() == now.date()
    kind = "out" if checked_in_today else "in"
    db.add(AttendanceRecord(technician_id=tech.id, kind=kind, site=site, score=round(primary.score, 4), created_at=now))
    db.commit()
    return CheckInOut(
        status="checked-out" if kind == "out" else "checked-in", technician=out, time=now, score=primary.score
    )


def _log_failure(db: Session, site: str, reason: str, score: float | None) -> None:
    db.add(FailedAttempt(site=site, reason=reason[:40], best_score=None if score is None else round(score, 4)))
    db.commit()


def _expire_old_challenges(db: Session) -> None:
    db.execute(delete(UsedChallenge).where(UsedChallenge.expires_at < datetime.now(UTC) - timedelta(hours=1)))


def _records(db: Session, start: date, end: date, technician_id: int | None):
    q = (
        select(AttendanceRecord)
        .join(Technician)
        .where(AttendanceRecord.created_at >= datetime.combine(start, time.min, UTC))
        .where(AttendanceRecord.created_at < datetime.combine(end + timedelta(days=1), time.min, UTC))
        .order_by(AttendanceRecord.created_at.desc())
    )
    if technician_id:
        q = q.where(AttendanceRecord.technician_id == technician_id)
    return db.scalars(q).all()


def _period(start: date | None, end: date | None) -> tuple[date, date]:
    today = datetime.now(UTC).date()
    start, end = start or today, end or today
    if end < start:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "End date is before start date")
    if (end - start).days > 92:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Choose a range of 3 months or less")
    return start, end


@router.get("", response_model=list[AttendanceOut], dependencies=[Depends(require_admin)])
def list_attendance(
    start: date | None = Query(None),
    end: date | None = Query(None),
    technician_id: int | None = None,
    db: Session = Depends(get_db),
):
    s, e = _period(start, end)
    return [
        AttendanceOut(
            id=r.id,
            kind=r.kind,
            site=r.site,
            score=r.score,
            created_at=_as_utc(r.created_at),
            technician_id=r.technician_id,
            technician_name=r.technician.name,
            employee_code=r.technician.employee_code,
        )
        for r in _records(db, s, e, technician_id)
    ]


@router.get("/export.csv", dependencies=[Depends(require_admin)])
def export_csv(start: date | None = None, end: date | None = None, db: Session = Depends(get_db)):
    s, e = _period(start, end)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Date", "Time (UTC)", "Employee code", "Name", "Type", "Site", "Match score"])
    for r in reversed(_records(db, s, e, None)):
        ts = _as_utc(r.created_at)
        writer.writerow(
            [
                ts.date().isoformat(),
                ts.strftime("%H:%M:%S"),
                r.technician.employee_code,
                r.technician.name,
                "Check-in" if r.kind == "in" else "Check-out",
                r.site,
                f"{r.score:.3f}",
            ]
        )
    filename = f"attendance_{s.isoformat()}_{e.isoformat()}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/summary", dependencies=[Depends(require_admin)])
def summary(db: Session = Depends(get_db)):
    """Today at a glance: who's on site now, total present, and unrecognised scans."""
    today = datetime.combine(datetime.now(UTC).date(), time.min, UTC)
    records = db.scalars(
        select(AttendanceRecord).where(AttendanceRecord.created_at >= today).order_by(AttendanceRecord.created_at)
    ).all()
    latest: dict[int, AttendanceRecord] = {}
    for r in records:
        latest[r.technician_id] = r
    on_site = [r.technician.name for r in latest.values() if r.kind == "in"]
    failed = db.scalar(select(func.count()).select_from(FailedAttempt).where(FailedAttempt.created_at >= today))
    active = db.scalar(select(func.count()).select_from(Technician).where(Technician.active.is_(True)))
    return {
        "present_today": len(latest),
        "on_site_now": sorted(on_site),
        "unrecognised_today": failed,
        "active_technicians": active,
    }
