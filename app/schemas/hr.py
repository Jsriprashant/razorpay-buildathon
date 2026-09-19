"""Schemas specific to the HR inbox (fit badges alongside request data)."""
from __future__ import annotations

from app.schemas.requests import HiringRequestOut


class InboxItemOut(HiringRequestOut):
    pass
