from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    message: str
    link: str | None
    read_at: datetime | None
    created_at: datetime


class NotificationsOut(BaseModel):
    items: list[NotificationOut]
    unread_count: int


class MarkReadRequest(BaseModel):
    notification_id: int | None = None
