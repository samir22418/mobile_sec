from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EnrollmentToken


def generate_token() -> str:
    return f"aegis_enroll_{secrets.token_urlsafe(32)}"


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EnrollmentTokenService:
    def create(
        self,
        session: Session,
        *,
        label: str,
        device_id: str | None = None,
        created_by: str | None = None,
        expires_at: datetime | None = None,
    ) -> tuple[EnrollmentToken, str]:
        token = generate_token()
        record = EnrollmentToken(
            label=label,
            token_hash=hash_token(token),
            device_id=device_id,
            created_by=created_by,
            expires_at=expires_at,
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return record, token

    def authenticate(self, session: Session, token: str, device_id: str | None = None) -> bool:
        record = session.scalar(select(EnrollmentToken).where(EnrollmentToken.token_hash == hash_token(token)))
        if record is None or not record.is_active:
            return False
        now = utc_now()
        if record.expires_at is not None and record.expires_at < now:
            return False
        if record.device_id and device_id and record.device_id != device_id:
            return False
        record.last_used_at = now
        session.commit()
        return True

    def revoke(self, session: Session, token_id: int) -> EnrollmentToken | None:
        record = session.get(EnrollmentToken, token_id)
        if record is None:
            return None
        record.is_active = False
        session.commit()
        session.refresh(record)
        return record
