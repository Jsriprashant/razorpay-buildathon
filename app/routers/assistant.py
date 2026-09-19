from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import current_user, get_db, resolve_team_id
from app.models import AppUser
from app.schemas.assistant import (
    AssistantActionRequest,
    AssistantActionResponse,
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantConfigResponse,
)
from app.services import assistant_service
from app.services.assistant_tools import confirm_action


router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.get("/config", response_model=AssistantConfigResponse)
def config(user: AppUser = Depends(current_user)):
    return assistant_service.get_config()


@router.post("/chat", response_model=AssistantChatResponse)
def chat(
    payload: AssistantChatRequest,
    db: Session = Depends(get_db),
    user: AppUser = Depends(current_user),
):
    return assistant_service.chat(db, user, payload)


@router.post("/actions/confirm", response_model=AssistantActionResponse)
def run_confirmed_action(
    payload: AssistantActionRequest,
    db: Session = Depends(get_db),
    user: AppUser = Depends(current_user),
):
    team_id = resolve_team_id(db, user, None)
    return confirm_action(db, user, team_id, payload.action)
