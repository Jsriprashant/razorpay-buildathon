"""Import every model module so Base.metadata sees all tables for create_all."""
from app.database import Base  # noqa: F401
from app.models.enums import (  # noqa: F401
    ApplicationStatus,
    ApprovalAction,
    CycleStatus,
    EngagementStatus,
    PositionStatus,
    PostingStatus,
    RequestSource,
    RequestStatus,
    RequestType,
    Role,
    VendorMessageStatus,
    WorkerSource,
)
from app.models.org import AppUser, Setting, Team  # noqa: F401
from app.models.planning import Cycle, CycleSummary, PlanLine  # noqa: F401
from app.models.postings import Application, JobPosting  # noqa: F401
from app.models.requests import ApprovalEvent, HiringRequest, Position  # noqa: F401
from app.models.system import AssistantActionGrant, AuditLog, Notification, ReconResolution  # noqa: F401
from app.models.vendors import VendorCompany, VendorEngagement, VendorMessage  # noqa: F401
from app.models.workforce import SnapshotWorker, Worker  # noqa: F401

__all__ = [
    "Base",
    "Team",
    "AppUser",
    "Setting",
    "Worker",
    "SnapshotWorker",
    "PlanLine",
    "Cycle",
    "CycleSummary",
    "VendorCompany",
    "HiringRequest",
    "Position",
    "ApprovalEvent",
    "JobPosting",
    "Application",
    "VendorEngagement",
    "VendorMessage",
    "ReconResolution",
    "Notification",
    "AuditLog",
    "AssistantActionGrant",
    "Role",
    "WorkerSource",
    "CycleStatus",
    "RequestType",
    "RequestSource",
    "RequestStatus",
    "ApprovalAction",
    "PositionStatus",
    "PostingStatus",
    "ApplicationStatus",
    "EngagementStatus",
    "VendorMessageStatus",
]
