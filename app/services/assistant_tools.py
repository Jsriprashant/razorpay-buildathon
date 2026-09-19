"""Product-specific tools exposed to the HeadcountHQ copilot.

Read tools call the same deterministic services as the UI. Write tools only
prepare a PendingAction; a separate authenticated confirmation endpoint
performs the mutation after the user explicitly approves it.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import (
    AppUser,
    HiringRequest,
    PlanLine,
    RequestStatus,
    RequestType,
    Role,
    VendorCompany,
    Worker,
)
from app.schemas.assistant import AssistantActionResponse, PendingAction
from app.schemas.forecast import WhatIfRequest
from app.schemas.plan import PlanLineIn
from app.schemas.requests import HiringRequestCreate
from app.services import forecast_service, kpi_service, plan_service, request_service
from app.services.clock import get_today


READ_TOOL_SPECS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "get_headcount_overview",
        "description": "Get the team's current KPI cards and variance summary.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_roster",
        "description": "Inspect the team's workers. Use optional text search to narrow by name, title, grade, location, or cost center.",
        "parameters": {
            "type": "object",
            "properties": {
                "search": {"type": ["string", "null"]},
                "include_inactive": {"type": "boolean"},
            },
            "required": ["search", "include_inactive"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_hiring_requests",
        "description": "Get recent hiring requests, optionally filtered by status or request type.",
        "parameters": {
            "type": "object",
            "properties": {
                "status": {
                    "type": ["string", "null"],
                    "enum": [None, "DRAFT", "SUBMITTED", "APPROVED", "REJECTED", "CHANGES_REQUESTED", "CANCELLED"],
                },
                "request_type": {"type": ["string", "null"], "enum": [None, "FTE", "VENDOR"]},
            },
            "required": ["status", "request_type"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_forecast",
        "description": "Get the deterministic baseline forecast, plan gaps, projected costs, and recommended hiring actions.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        "strict": True,
    },
    {
        "type": "function",
        "name": "run_forecast_scenario",
        "description": "Run a non-destructive what-if forecast. Percent attrition is a decimal: 0.02 means 2% monthly.",
        "parameters": {
            "type": "object",
            "properties": {
                "hiring_delay_months": {"type": "integer", "minimum": 0, "maximum": 12},
                "attrition_pct_override": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
                "hiring_freeze_from_month": {
                    "type": ["string", "null"],
                    "description": "YYYY-MM-01",
                },
                "extra_hires": {"type": "integer", "minimum": 0, "maximum": 500},
                "extra_hires_type": {"type": "string", "enum": ["FTE", "VENDOR"]},
                "extra_hires_start_month": {
                    "type": ["string", "null"],
                    "description": "YYYY-MM-01",
                },
                "extra_hires_unit_cost_cents": {"type": ["integer", "null"], "minimum": 0},
            },
            "required": [
                "hiring_delay_months",
                "attrition_pct_override",
                "hiring_freeze_from_month",
                "extra_hires",
                "extra_hires_type",
                "extra_hires_start_month",
                "extra_hires_unit_cost_cents",
            ],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_vendor_companies",
        "description": "List vendor companies and their IDs before preparing a vendor hiring request.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        "strict": True,
    },
]


WRITE_TOOL_SPECS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "prepare_hiring_request",
        "description": "Prepare a draft FTE or vendor hiring request for user confirmation. This does not write data.",
        "parameters": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["FTE", "VENDOR"]},
                "role_title": {"type": "string"},
                "grade": {"type": ["string", "null"]},
                "quantity": {"type": "integer", "minimum": 1, "maximum": 100},
                "annual_salary_cents": {"type": ["integer", "null"], "minimum": 1},
                "vendor_company_id": {"type": ["integer", "null"]},
                "hourly_rate_cents": {"type": ["integer", "null"], "minimum": 1},
                "hours_per_month": {"type": ["integer", "null"], "minimum": 1, "maximum": 744},
                "target_start_date": {"type": "string", "description": "YYYY-MM-DD"},
                "end_date": {"type": ["string", "null"], "description": "YYYY-MM-DD"},
                "justification": {"type": "string"},
            },
            "required": [
                "type",
                "role_title",
                "grade",
                "quantity",
                "annual_salary_cents",
                "vendor_company_id",
                "hourly_rate_cents",
                "hours_per_month",
                "target_start_date",
                "end_date",
                "justification",
            ],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "prepare_plan_update",
        "description": "Prepare an update to one monthly plan line for confirmation. All three values must be supplied.",
        "parameters": {
            "type": "object",
            "properties": {
                "month_start": {"type": "string", "description": "YYYY-MM-01"},
                "planned_fte_hc": {"type": "integer", "minimum": 0},
                "planned_vendor_hc": {"type": "integer", "minimum": 0},
                "planned_budget_cents": {"type": "integer", "minimum": 0},
            },
            "required": ["month_start", "planned_fte_hc", "planned_vendor_hc", "planned_budget_cents"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "prepare_request_submission",
        "description": "Prepare submission of an existing draft or changes-requested hiring request for confirmation.",
        "parameters": {
            "type": "object",
            "properties": {"request_id": {"type": "integer", "minimum": 1}},
            "required": ["request_id"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


def available_tool_specs(user: AppUser) -> list[dict[str, Any]]:
    if user.role in (Role.MANAGER, Role.HR):
        return READ_TOOL_SPECS + WRITE_TOOL_SPECS
    return READ_TOOL_SPECS


def _json(model: Any) -> Any:
    return model.model_dump(mode="json") if hasattr(model, "model_dump") else model


def execute_tool(
    db: Session,
    user: AppUser,
    team_id: int,
    name: str,
    arguments: dict[str, Any],
) -> tuple[Any, PendingAction | None]:
    today = get_today(db)

    if name == "get_headcount_overview":
        return _json(kpi_service.compute_kpis(db, team_id, today)), None

    if name == "get_roster":
        search = (arguments.get("search") or "").strip().lower()
        include_inactive = bool(arguments.get("include_inactive"))
        workers = db.query(Worker).filter(Worker.team_id == team_id).order_by(Worker.name).all()
        rows = []
        for worker in workers:
            if not include_inactive and worker.termination_date and worker.termination_date < today:
                continue
            haystack = " ".join(
                [worker.name, worker.job_title, worker.grade, worker.location, worker.cost_center]
            ).lower()
            if search and search not in haystack:
                continue
            rows.append(
                {
                    "worker_id": worker.worker_id,
                    "name": worker.name,
                    "job_title": worker.job_title,
                    "grade": worker.grade,
                    "location": worker.location,
                    "cost_center": worker.cost_center,
                    "hire_date": worker.hire_date.isoformat(),
                    "termination_date": worker.termination_date.isoformat() if worker.termination_date else None,
                    "annual_salary_cents": worker.annual_salary_cents,
                }
            )
        return {"count": len(rows), "workers": rows[:100], "truncated": len(rows) > 100}, None

    if name == "get_hiring_requests":
        status_value = arguments.get("status")
        type_value = arguments.get("request_type")
        request_status = RequestStatus(status_value) if status_value else None
        request_type = RequestType(type_value) if type_value else None
        requests = request_service.list_requests(db, team_id, request_status, request_type, None, "-created_at")
        return {
            "count": len(requests),
            "requests": [
                {
                    "id": row.id,
                    "type": row.type.value,
                    "role_title": row.role_title,
                    "grade": row.grade,
                    "quantity": row.quantity,
                    "status": row.status.value,
                    "target_start_date": row.target_start_date.isoformat(),
                    "annual_salary_cents": row.annual_salary_cents,
                    "hourly_rate_cents": row.hourly_rate_cents,
                    "created_at": row.created_at.isoformat(),
                }
                for row in requests[:75]
            ],
            "truncated": len(requests) > 75,
        }, None

    if name == "get_forecast":
        return _json(forecast_service.compute_forecast(db, team_id, today)), None

    if name == "run_forecast_scenario":
        scenario = WhatIfRequest.model_validate(arguments)
        return _json(forecast_service.compute_what_if(db, team_id, today, scenario)), None

    if name == "get_vendor_companies":
        vendors = db.query(VendorCompany).order_by(VendorCompany.name).all()
        return {"vendors": [{"id": v.id, "name": v.name} for v in vendors]}, None

    if user.role not in (Role.MANAGER, Role.HR):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your role cannot change data")

    if name == "prepare_hiring_request":
        validated = HiringRequestCreate.model_validate(arguments)
        data = validated.model_dump(mode="json")
        action = PendingAction(
            kind="create_hiring_request",
            title=f"Create {validated.quantity} {validated.type.value} request for {validated.role_title}",
            description="Creates a draft hiring request. It will not be submitted to HR yet.",
            payload=data,
        )
        return {"status": "awaiting_user_confirmation", "action": action.model_dump(mode="json")}, action

    if name == "prepare_plan_update":
        validated = PlanLineIn.model_validate(arguments)
        action = PendingAction(
            kind="update_plan_month",
            title=f"Update plan for {validated.month_start.strftime('%B %Y')}",
            description=(
                f"Set planned FTE to {validated.planned_fte_hc}, vendors to "
                f"{validated.planned_vendor_hc}, and budget to "
                f"{validated.planned_budget_cents / 100:,.2f}."
            ),
            payload=validated.model_dump(mode="json"),
        )
        return {"status": "awaiting_user_confirmation", "action": action.model_dump(mode="json")}, action

    if name == "prepare_request_submission":
        request_id = int(arguments["request_id"])
        request = db.get(HiringRequest, request_id)
        if request is None or request.team_id != team_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hiring request not found")
        if request.status not in (RequestStatus.DRAFT, RequestStatus.CHANGES_REQUESTED):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Request {request_id} cannot be submitted from {request.status.value}",
            )
        action = PendingAction(
            kind="submit_hiring_request",
            title=f"Submit request #{request.id}: {request.role_title}",
            description="Sends this request to HR for review and creates the normal notification.",
            payload={"request_id": request.id},
        )
        return {"status": "awaiting_user_confirmation", "action": action.model_dump(mode="json")}, action

    raise ValueError(f"Unknown assistant tool: {name}")


def confirm_action(
    db: Session,
    user: AppUser,
    team_id: int,
    action: PendingAction,
) -> AssistantActionResponse:
    if user.role not in (Role.MANAGER, Role.HR):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your role cannot change data")

    if action.kind == "create_hiring_request":
        payload = HiringRequestCreate.model_validate(action.payload)
        created = request_service.create_request(db, team_id, payload, user)
        return AssistantActionResponse(
            message=f"Draft request #{created.id} for {created.role_title} was created.",
            link=f"/requests/{created.id}",
            entity_id=created.id,
        )

    if action.kind == "update_plan_month":
        line = PlanLineIn.model_validate(action.payload)
        plan_service.upsert_plan(db, team_id, [line])
        return AssistantActionResponse(
            message=f"The plan for {line.month_start.strftime('%B %Y')} was updated.",
            link="/plan",
        )

    if action.kind == "submit_hiring_request":
        request_id = int(action.payload["request_id"])
        request = db.get(HiringRequest, request_id)
        if request is None or request.team_id != team_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hiring request not found")
        if request.status == RequestStatus.CHANGES_REQUESTED:
            submitted = request_service.resubmit_request(db, team_id, request_id, user)
        else:
            submitted = request_service.submit_request(db, team_id, request_id, user)
        return AssistantActionResponse(
            message=f"Request #{submitted.id} was submitted to HR.",
            link=f"/requests/{submitted.id}",
            entity_id=submitted.id,
        )

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported assistant action")
