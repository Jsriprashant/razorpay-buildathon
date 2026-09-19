from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.deps import current_user, get_db, require_manager_or_hr, resolve_team_id
from app.models import AppUser
from app.schemas.recon import ReconBulkResolveRequest, ReconLinkPositionRequest, ReconOut, ReconResolveRequest
from app.services import recon_service
from app.services.clock import get_today

router = APIRouter(prefix="/recon", tags=["recon"])


@router.get("", response_model=ReconOut)
def get_recon(
    month: date | None = Query(default=None),
    team_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AppUser = Depends(current_user),
):
    today = get_today(db)
    scoped_team_id = resolve_team_id(db, user, team_id)
    period_month = date((month or today).year, (month or today).month, 1)
    return recon_service.get_recon(db, scoped_team_id, period_month, today)


@router.post("/resolve")
def resolve(
    payload: ReconResolveRequest,
    team_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AppUser = Depends(require_manager_or_hr),
):
    scoped_team_id = resolve_team_id(db, user, team_id)
    recon_service.resolve_flag(db, scoped_team_id, payload, user)
    return {"ok": True}


@router.post("/resolve/bulk")
def resolve_bulk(
    payload: ReconBulkResolveRequest,
    team_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AppUser = Depends(require_manager_or_hr),
):
    scoped_team_id = resolve_team_id(db, user, team_id)
    for item in payload.items:
        recon_service.resolve_flag(db, scoped_team_id, item, user)
    return {"ok": True, "count": len(payload.items)}


@router.post("/link-position")
def link_position(
    payload: ReconLinkPositionRequest,
    team_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AppUser = Depends(require_manager_or_hr),
):
    scoped_team_id = resolve_team_id(db, user, team_id)
    try:
        recon_service.link_position(db, scoped_team_id, payload.worker_pk, payload.position_id, user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"ok": True}
