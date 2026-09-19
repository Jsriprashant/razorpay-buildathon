from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


ReasoningEffort = Literal["none", "low", "medium", "high", "max"]
ChatRole = Literal["user", "assistant"]


class AssistantMessage(BaseModel):
    role: ChatRole
    content: str = Field(min_length=1, max_length=12_000)


class PendingAction(BaseModel):
    kind: Literal["create_hiring_request", "update_plan_month", "submit_hiring_request"]
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=1_000)
    payload: dict[str, Any]


class AssistantChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8_000)
    history: list[AssistantMessage] = Field(default_factory=list, max_length=30)
    model: str = Field(default="auto", max_length=100)
    reasoning_effort: ReasoningEffort = "medium"


class ToolActivity(BaseModel):
    name: str
    label: str


class AssistantChatResponse(BaseModel):
    answer: str
    model_used: str
    tool_activity: list[ToolActivity] = Field(default_factory=list)
    pending_action: PendingAction | None = None


class AssistantActionRequest(BaseModel):
    action: PendingAction


class AssistantActionResponse(BaseModel):
    message: str
    link: str | None = None
    entity_id: int | None = None


class AssistantModelOption(BaseModel):
    id: str
    label: str
    supports_reasoning: bool


class AssistantConfigResponse(BaseModel):
    models: list[AssistantModelOption]
    default_model: str
