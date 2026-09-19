from sqlalchemy.orm import Session

from app.models import AppUser


def list_demo_users(db: Session) -> list[AppUser]:
    return db.query(AppUser).order_by(AppUser.role, AppUser.name).all()


def get_user(db: Session, user_id: int) -> AppUser | None:
    return db.get(AppUser, user_id)


def get_user_by_email(db: Session, email: str) -> AppUser | None:
    return db.query(AppUser).filter(AppUser.email == email).first()
