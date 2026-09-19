from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import current_user, get_db
from app.models import AppUser
from app.schemas.notifications import MarkReadRequest, NotificationOut, NotificationsOut
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _out(db: Session, user: AppUser) -> NotificationsOut:
    items = notification_service.list_for_user(db, user.id)
    unread = notification_service.unread_count(db, user.id)
    return NotificationsOut(items=[NotificationOut.model_validate(n) for n in items], unread_count=unread)


@router.get("", response_model=NotificationsOut)
def list_notifications(db: Session = Depends(get_db), user: AppUser = Depends(current_user)):
    return _out(db, user)


@router.post("/read", response_model=NotificationsOut)
def mark_read(
    payload: MarkReadRequest,
    db: Session = Depends(get_db),
    user: AppUser = Depends(current_user),
):
    notification_service.mark_read(db, user.id, payload.notification_id)
    return _out(db, user)
