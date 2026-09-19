from pydantic import BaseModel, ConfigDict

from app.models.enums import Role


class DemoUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: Role
    team_id: int | None


class LoginRequest(BaseModel):
    user_id: int


class CurrentUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: Role
    team_id: int | None
    team_name: str | None = None
