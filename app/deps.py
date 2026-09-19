"""Shared FastAPI dependencies: DB session, current-user auth, role/team guards.

Every route depends on `current_user` (or one of the role-restricted variants)
so that role and team scoping is enforced on the server, never assumed from
the client. See Section 13 of the spec.
"""
from collections.abc import Generator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import AppUser, Role, Team


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def current_user(request: Request, db: Session = Depends(get_db)) -> AppUser:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not logged in")
    user = db.get(AppUser, user_id)
    if user is None:
        request.session.clear()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session user no longer exists")
    return user


def require_roles(*roles: Role):
    def _guard(user: AppUser = Depends(current_user)) -> AppUser:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted for this role")
        return user

    return _guard


require_hr = require_roles(Role.HR)
require_manager = require_roles(Role.MANAGER)
require_manager_or_hr = require_roles(Role.MANAGER, Role.HR)


def assert_team_scope(user: AppUser, team_id: int) -> None:
    """A MANAGER may only ever touch their own team's data; HR and
    FINANCE_VIEWER can read/act across teams. Call this in every service
    function that takes a team_id, not just in the router."""
    if user.role == Role.MANAGER and user.team_id != team_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your team")


def resolve_team_id(db, user: AppUser, team_id: int | None) -> int:
    """Every team-scoped route accepts an optional ?team_id=. A MANAGER is
    pinned to their own team (403 if they ask for another); HR/FINANCE_VIEWER
    may pass any team_id, or omit it to get the first team (there is exactly
    one team in this build, but this keeps the door open for more)."""
    if user.role == Role.MANAGER:
        if user.team_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Manager has no team assigned")
        if team_id is not None and team_id != user.team_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your team")
        return user.team_id
    if team_id is not None:
        return team_id
    first_team = db.query(Team).order_by(Team.id).first()
    if first_team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No teams exist")
    return first_team.id
