"""Shared enum types for the data model (Section 3 of the spec)."""
import enum


class Role(str, enum.Enum):
    MANAGER = "MANAGER"
    HR = "HR"
    FINANCE_VIEWER = "FINANCE_VIEWER"


class WorkerSource(str, enum.Enum):
    SEED = "SEED"
    MANUAL = "MANUAL"
    HIRED_FROM_POSTING = "HIRED_FROM_POSTING"


class CycleStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class RequestType(str, enum.Enum):
    FTE = "FTE"
    VENDOR = "VENDOR"


class RequestSource(str, enum.Enum):
    MANUAL = "MANUAL"
    FORECAST_SUGGESTION = "FORECAST_SUGGESTION"


class RequestStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    CANCELLED = "CANCELLED"


class ApprovalAction(str, enum.Enum):
    SUBMIT = "SUBMIT"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REQUEST_CHANGES = "REQUEST_CHANGES"
    CANCEL = "CANCEL"
    RESUBMIT = "RESUBMIT"


class PositionStatus(str, enum.Enum):
    OPEN = "OPEN"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"


class PostingStatus(str, enum.Enum):
    PUBLISHED = "PUBLISHED"
    PAUSED = "PAUSED"
    CLOSED = "CLOSED"


class ApplicationStatus(str, enum.Enum):
    NEW = "NEW"
    SHORTLISTED = "SHORTLISTED"
    REJECTED = "REJECTED"
    HIRED = "HIRED"


class EngagementStatus(str, enum.Enum):
    AWAITING_DISPATCH = "AWAITING_DISPATCH"
    MESSAGE_SENT = "MESSAGE_SENT"
    CONFIRMED = "CONFIRMED"
    DECLINED = "DECLINED"
    CANCELLED = "CANCELLED"


class VendorMessageStatus(str, enum.Enum):
    SENT = "SENT"
    REPLIED = "REPLIED"
