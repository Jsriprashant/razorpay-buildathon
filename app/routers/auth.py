from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.deps import current_user, get_db
from app.models import AppUser
from app.schemas.auth import CurrentUserOut, DemoUserOut, LoginRequest
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/demo-users", response_model=list[DemoUserOut])
def demo_users(db: Session = Depends(get_db)):
    """Public: powers the demo login picker. Never returns anything more
    sensitive than name/email/role/team — no salary, no session data."""
    return auth_service.list_demo_users(db)


@router.post("/login", response_model=CurrentUserOut)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = auth_service.get_user(db, payload.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown demo user")
    request.session["user_id"] = user.id
    return CurrentUserOut(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        team_id=user.team_id,
        team_name=user.team.name if user.team else None,
    )


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@router.get("/me", response_model=CurrentUserOut)
def me(user: AppUser = Depends(current_user)):
    return CurrentUserOut(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        team_id=user.team_id,
        team_name=user.team.name if user.team else None,
    )
