from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import current_user, get_db, resolve_team_id
from app.models import AppUser
from app.schemas.kpi import KpiOut
from app.services import kpi_service
from app.services.clock import get_today

router = APIRouter(prefix="/kpis", tags=["kpis"])


@router.get("", response_model=KpiOut)
def get_kpis(
    team_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AppUser = Depends(current_user),
):
    today = get_today(db)
    scoped_team_id = resolve_team_id(db, user, team_id)
    return kpi_service.compute_kpis(db, scoped_team_id, today)
