"""Shared audit-log writer used by every service in the hiring/HR/vendor
pipeline (Section 2: every mutation is audited). Kept as its own module
(rather than duplicated per service, as roster_service does locally) so the
whole pipeline writes audit rows the same way."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import AuditLog


def write_audit(
    db: Session,
    actor_id: int | None,
    entity: str,
    entity_id: int,
    action: str,
    detail: str | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor_id,
            entity=entity,
            entity_id=entity_id,
            action=action,
            detail_json=detail,
            at=datetime.utcnow(),
        )
    )
