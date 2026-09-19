"""Writes Notification rows. No bell UI reads these yet (that's the
rollover/notifications/history task) — this module only guarantees the rows
exist so that task can build the inbox UI without a backfill.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import AppUser, Notification, Role


def notify_user(db: Session, user_id: int, message: str, link: str | None = None) -> None:
    db.add(Notification(user_id=user_id, message=message, link=link, created_at=datetime.utcnow()))


def notify_role(db: Session, role: Role, message: str, link: str | None = None) -> None:
    user_ids = [row[0] for row in db.query(AppUser.id).filter(AppUser.role == role).all()]
    for user_id in user_ids:
        notify_user(db, user_id, message, link)


def notification_exists(db: Session, user_id: int, message: str) -> bool:
    """Dedup guard for notifications that could otherwise be generated
    repeatedly on every page load (e.g. "contract expiring soon")."""
    return (
        db.query(Notification.id)
        .filter(Notification.user_id == user_id, Notification.message == message)
        .first()
        is not None
    )


def list_for_user(db: Session, user_id: int, limit: int = 50) -> list[Notification]:
    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )


def unread_count(db: Session, user_id: int) -> int:
    return (
        db.query(Notification.id)
        .filter(Notification.user_id == user_id, Notification.read_at.is_(None))
        .count()
    )


def mark_read(db: Session, user_id: int, notification_id: int | None) -> None:
    """notification_id=None marks every unread notification for this user as
    read (the bell's "mark all read" action); otherwise marks just the one
    (and only if it belongs to this user)."""
    query = db.query(Notification).filter(Notification.user_id == user_id, Notification.read_at.is_(None))
    if notification_id is not None:
        query = query.filter(Notification.id == notification_id)
    query.update({Notification.read_at: datetime.utcnow()}, synchronize_session=False)
    db.commit()
