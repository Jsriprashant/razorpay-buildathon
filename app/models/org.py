"""Team, user and settings tables."""
from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import Role


class Team(Base):
    __tablename__ = "team"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    cost_center: Mapped[str] = mapped_column(String(50), nullable=False)
    # Circular reference to worker.id — declared with use_alter to let
    # create_all/drop_all sequence the two tables without a hard cycle.
    manager_worker_id: Mapped[int | None] = mapped_column(
        ForeignKey("worker.id", use_alter=True, name="fk_team_manager_worker"),
        nullable=True,
    )

    users: Mapped[list["AppUser"]] = relationship(back_populates="team")
    workers: Mapped[list["Worker"]] = relationship(
        back_populates="team", foreign_keys="Worker.team_id"
    )


class AppUser(Base):
    __tablename__ = "app_user"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    role: Mapped[Role] = mapped_column(nullable=False)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("team.id"), nullable=True, index=True)

    team: Mapped[Team | None] = relationship(back_populates="users")


class Setting(Base):
    __tablename__ = "setting"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
