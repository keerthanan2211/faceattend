from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class Technician(Base):
    __tablename__ = "technicians"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    trade: Mapped[str] = mapped_column(String(50))  # e.g. "Electrician", "Surveyor"
    phone: Mapped[str] = mapped_column(String(15))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    faces: Mapped[list["FaceTemplate"]] = relationship(cascade="all, delete-orphan", passive_deletes=True)


class FaceTemplate(Base):
    """A face embedding (never the photo), encrypted with AES-256-GCM. See app/crypto.py."""

    __tablename__ = "face_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    technician_id: Mapped[int] = mapped_column(ForeignKey("technicians.id", ondelete="CASCADE"), index=True)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AttendanceRecord(Base):
    __tablename__ = "attendance"

    id: Mapped[int] = mapped_column(primary_key=True)
    technician_id: Mapped[int] = mapped_column(ForeignKey("technicians.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(3))  # "in" | "out"
    site: Mapped[str] = mapped_column(String(80))
    score: Mapped[float] = mapped_column(Float)  # match similarity, kept for auditing
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)

    technician: Mapped[Technician] = relationship()


class FailedAttempt(Base):
    """Unrecognised scans, so admins can spot enrolment problems or misuse."""

    __tablename__ = "failed_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    site: Mapped[str] = mapped_column(String(80))
    reason: Mapped[str] = mapped_column(String(40))  # e.g. "below-threshold", "liveness:no-turn"
    best_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class UsedChallenge(Base):
    """Nonces of liveness challenges already used, so a captured challenge can't be replayed."""

    __tablename__ = "used_challenges"

    nonce: Mapped[str] = mapped_column(String(32), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
