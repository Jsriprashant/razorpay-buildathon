"""OpenAI Responses API harness for the CONTINUUM copilot."""
from __future__ import annotations

import json
import os
import time
from collections.abc import Iterator
from typing import Any

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.deps import resolve_team_id
from app.models import AppUser
from app.schemas.assistant import (
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantConfigResponse,
    AssistantModelOption,
    ToolActivity,
)
from app.services.assistant_tools import available_tool_specs, execute_tool
from app.services.assistant_skills import skill_instructions


MODEL_OPTIONS = [
    AssistantModelOption(id="auto", label="Auto", supports_reasoning=True),
    AssistantModelOption(id="gpt-5-mini", label="GPT-5 mini", supports_reasoning=True),
    AssistantModelOption(id="gpt-5", label="GPT-5", supports_reasoning=True),
    AssistantModelOption(id="gpt-4.1-mini", label="GPT-4.1 mini", supports_reasoning=False),
    AssistantModelOption(id="gpt-4.1", label="GPT-4.1", supports_reasoning=False),
]
ALLOWED_MODELS = {option.id for option in MODEL_OPTIONS}
AUTO_MODEL = "gpt-5-mini"
REASONING_MODELS = {"gpt-5", "gpt-5-mini"}
REASONING_MAP = {"none": "minimal", "low": "low", "medium": "medium", "high": "high", "max": "high"}
INITIAL_OUTPUT_TOKENS = 6_000
FINAL_OUTPUT_TOKENS = 10_000
MAX_OUTPUT_TOKENS = 16_000
MAX_HISTORY_CHARS = 24_000
MAX_TOOL_RESULT_ITEMS = 50
MAX_PROVIDER_ATTEMPTS = 3
TOOL_LABELS = {
    "get_headcount_overview": "Reviewed headcount KPIs",
    "get_roster": "Searched the roster",
    "get_hiring_requests": "Reviewed hiring requests",
    "get_forecast": "Reviewed the forecast",
    "run_forecast_scenario": "Ran a forecast scenario",
    "get_vendor_companies": "Reviewed vendor companies",
    "prepare_hiring_request": "Prepared a hiring request",
    "prepare_plan_update": "Prepared a plan update",
    "prepare_request_submission": "Prepared a request submission",
}


def get_config() -> AssistantConfigResponse:
    return AssistantConfigResponse(models=MODEL_OPTIONS, default_model="auto")


def _choose_auto_model(message: str, reasoning_effort: str) -> str:
    complex_terms = (
        "compare",
        "scenario",
        "forecast",
        "strategy",
        "recommend",
        "tradeoff",
        "trade-off",
        "why",
        "analyze",
        "plan",
    )
    is_complex = reasoning_effort in {"high", "max"} or any(term in message.lower() for term in complex_terms)
    return "gpt-5" if is_complex else AUTO_MODEL


def _system_prompt(user: AppUser, team_id: int, message: str) -> str:
    return f"""You are CONTINUUM Copilot, embedded in CONTINUUM.

User context:
- Name: {user.name}
- Role: {user.role.value}
- Scoped team id: {team_id}

Your job is to explain the user's live workforce data, surface useful insights,
compare deterministic forecast scenarios, and help complete CONTINUUM work.

Rules:
1. Use tools whenever the answer depends on live product data. Never invent
   counts, costs, workers, requests, dates, or forecast outputs.
2. Treat tool results as the source of truth. State important assumptions.
3. Keep answers concise and decision-oriented. Use bullets or a small table
   when comparing scenarios. Money values from tools are integer cents.
4. Never reveal hidden chain-of-thought. Give short conclusions, calculations,
   and sources used instead.
5. Never claim a write happened unless a confirmed action result says it did.
   Write tools only prepare a confirmation card.
6. Do not expose data outside the user's team scope. Do not request secrets.
7. Forecasts are deterministic scenario calculations, not predictions from AI.
8. If required action fields are missing, ask a focused follow-up instead of
   guessing salary, dates, vendor, grade, headcount, or budget.
9. Format the final answer as clear GitHub-flavored Markdown. Use descriptive
   headings, compact tables for comparisons, bullets for findings, and bold
   values for important numbers. Do not use a table when a short sentence is
   clearer. Always include a short "Data used" section naming the live product
   areas/tools consulted. Never output raw JSON or internal tool names.

Product skills loaded for this request:
{skill_instructions(message)}
"""


def _extract_text(output: list[dict[str, Any]]) -> str:
    chunks: list[str] = []
    for item in output:
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                chunks.append(content["text"])
    return "\n".join(chunks).strip()


def _compact_history(payload: AssistantChatRequest) -> list[dict[str, str]]:
    """Keep the newest useful history without repeatedly sending huge transcripts."""
    selected: list[dict[str, str]] = []
    remaining = MAX_HISTORY_CHARS
    for item in reversed(payload.history):
        if remaining <= 0:
            break
        content = item.content[-remaining:]
        selected.append({"role": item.role, "content": content})
        remaining -= len(content)
    return list(reversed(selected))


def _compact_tool_result(value: Any) -> Any:
    """Bound large live-data payloads while preserving their shape and totals."""
    if isinstance(value, list):
        compacted = [_compact_tool_result(item) for item in value[:MAX_TOOL_RESULT_ITEMS]]
        if len(value) > MAX_TOOL_RESULT_ITEMS:
            compacted.append(
                {
                    "_truncated": True,
                    "_returned_items": MAX_TOOL_RESULT_ITEMS,
                    "_total_items": len(value),
                }
            )
        return compacted
    if isinstance(value, dict):
        return {key: _compact_tool_result(item) for key, item in value.items()}
    if isinstance(value, str) and len(value) > 4_000:
        return value[:4_000] + "…"
    return value


def _serialize_tool_result(value: Any) -> str:
    return json.dumps(_compact_tool_result(value), default=str)


def _post_with_retry(
    client: httpx.Client,
    headers: dict[str, str],
    request_body: dict[str, Any],
) -> httpx.Response:
    """Retry only temporary provider failures; never replay product actions."""
    for attempt in range(MAX_PROVIDER_ATTEMPTS):
        try:
            response = client.post(
                "https://api.openai.com/v1/responses",
                headers=headers,
                json=request_body,
            )
        except httpx.RequestError:
            if attempt == MAX_PROVIDER_ATTEMPTS - 1:
                raise
            time.sleep(0.5 * (2**attempt))
            continue
        if response.status_code not in {429, 500, 502, 503, 504}:
            return response
        if attempt == MAX_PROVIDER_ATTEMPTS - 1:
            return response
        retry_after = response.headers.get("retry-after")
        try:
            delay = min(float(retry_after), 4.0) if retry_after else 0.5 * (2**attempt)
        except ValueError:
            delay = 0.5 * (2**attempt)
        time.sleep(delay)
    raise RuntimeError("unreachable")


def _sse(event: str, data: dict[str, Any]) -> str:
    """Serialize one named server-sent event."""
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def _provider_error(response: httpx.Response) -> str:
    detail = "The AI provider could not complete this request."
    try:
        provider_error = response.json().get("error", {}).get("message")
        if provider_error:
            detail = provider_error
    except ValueError:
        pass
    return detail


def _stream_provider_response(
    client: httpx.Client,
    headers: dict[str, str],
    request_body: dict[str, Any],
) -> Iterator[dict[str, Any]]:
    """Yield parsed Responses API SSE events without exposing hidden reasoning."""
    with client.stream(
        "POST",
        "https://api.openai.com/v1/responses",
        headers=headers,
        json={**request_body, "stream": True},
    ) as response:
        if response.status_code >= 400:
            response.read()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=_provider_error(response),
            )
        for line in response.iter_lines():
            if not line.startswith("data: "):
                continue
            raw = line[6:]
            if raw == "[DONE]":
                break
            try:
                yield json.loads(raw)
            except json.JSONDecodeError:
                continue


def chat_stream(
    db: Session,
    user: AppUser,
    payload: AssistantChatRequest,
) -> Iterator[str]:
    """Stream progress, tool activity, answer Markdown, and action proposals."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        yield _sse("error", {"message": "CONTINUUM Copilot is not configured."})
        return
    if payload.model not in ALLOWED_MODELS:
        yield _sse("error", {"message": "Unsupported assistant model"})
        return

    model = (
        _choose_auto_model(payload.message, payload.reasoning_effort)
        if payload.model == "auto"
        else payload.model
    )
    team_id = resolve_team_id(db, user, None)
    conversation: list[dict[str, Any]] = [
        {"role": "developer", "content": _system_prompt(user, team_id, payload.message)}
    ]
    conversation.extend(_compact_history(payload))
    conversation.append({"role": "user", "content": payload.message})
    request_body: dict[str, Any] = {
        "model": model,
        "input": conversation,
        "tools": available_tool_specs(user),
        "tool_choice": "auto",
        "max_output_tokens": INITIAL_OUTPUT_TOKENS,
    }
    if model in REASONING_MODELS:
        request_body["reasoning"] = {"effort": REASONING_MAP[payload.reasoning_effort]}

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    pending_action = None
    activities: list[ToolActivity] = []
    answer_parts: list[str] = []

    yield _sse(
        "status",
        {
            "stage": "starting",
            "label": "Understanding your request",
            "model_used": model,
        },
    )

    try:
        with httpx.Client(timeout=90.0) as client:
            for step in range(8):
                output: list[dict[str, Any]] = []
                streamed_text = False
                provider_completed = False
                incomplete_reason: str | None = None
                yield _sse(
                    "status",
                    {
                        "stage": "analyzing" if step == 0 else "synthesizing",
                        "label": "Analyzing live workspace data" if step == 0 else "Preparing the answer",
                    },
                )
                for provider_event in _stream_provider_response(client, headers, request_body):
                    event_type = provider_event.get("type")
                    if event_type == "response.output_text.delta":
                        delta = provider_event.get("delta") or ""
                        if delta:
                            streamed_text = True
                            answer_parts.append(delta)
                            yield _sse("answer_delta", {"delta": delta})
                    elif event_type == "response.completed":
                        provider_completed = True
                        output = provider_event.get("response", {}).get("output", [])
                    elif event_type == "response.failed":
                        message = (
                            provider_event.get("response", {})
                            .get("error", {})
                            .get("message", "The AI provider could not complete this request.")
                        )
                        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=message)
                    elif event_type == "response.incomplete":
                        incomplete = provider_event.get("response", {})
                        output = incomplete.get("output", [])
                        incomplete_reason = (
                            incomplete.get("incomplete_details", {}).get("reason")
                            or "The AI provider ended the response before it was complete."
                        )

                if incomplete_reason:
                    if (
                        incomplete_reason == "max_output_tokens"
                        and request_body["max_output_tokens"] < MAX_OUTPUT_TOKENS
                    ):
                        partial = _extract_text(output)
                        if partial and not streamed_text:
                            answer_parts.append(partial)
                            yield _sse("answer_delta", {"delta": partial})
                        if partial:
                            conversation.append({"role": "assistant", "content": partial})
                            conversation.append(
                                {
                                    "role": "developer",
                                    "content": (
                                        "Continue exactly where the prior answer stopped. "
                                        "Do not repeat prior text. Finish concisely."
                                    ),
                                }
                            )
                        request_body["input"] = conversation
                        request_body["max_output_tokens"] = min(
                            request_body["max_output_tokens"] * 2,
                            MAX_OUTPUT_TOKENS,
                        )
                        if model in REASONING_MODELS:
                            request_body["reasoning"] = {"effort": "minimal"}
                        continue
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Incomplete assistant response: {incomplete_reason}",
                    )

                if not provider_completed:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="The assistant stream ended unexpectedly. Please try again.",
                    )

                calls = [item for item in output if item.get("type") == "function_call"]
                if not calls:
                    if not streamed_text:
                        answer = _extract_text(output)
                        if answer:
                            answer_parts.append(answer)
                            yield _sse("answer_delta", {"delta": answer})
                    yield _sse(
                        "done",
                        {
                            "answer": "".join(answer_parts).strip(),
                            "model_used": model,
                            "tool_activity": [activity.model_dump(mode="json") for activity in activities],
                            "pending_action": (
                                pending_action.model_dump(mode="json") if pending_action is not None else None
                            ),
                        },
                    )
                    return

                conversation.extend(output)
                for call in calls:
                    name = call.get("name", "")
                    label = TOOL_LABELS.get(name, name)
                    yield _sse("tool", {"name": name, "label": label, "state": "running"})
                    try:
                        arguments = json.loads(call.get("arguments") or "{}")
                        tool_result, proposed_action = execute_tool(db, user, team_id, name, arguments)
                        if proposed_action is not None:
                            pending_action = proposed_action
                        serialized = _serialize_tool_result(tool_result)
                        tool_state = "complete"
                    except HTTPException as exc:
                        serialized = json.dumps({"error": exc.detail, "status_code": exc.status_code})
                        tool_state = "error"
                    except (ValueError, TypeError, KeyError) as exc:
                        serialized = json.dumps({"error": f"Invalid tool input: {exc}"})
                        tool_state = "error"
                    activities.append(ToolActivity(name=name, label=label))
                    yield _sse("tool", {"name": name, "label": label, "state": tool_state})
                    conversation.append(
                        {
                            "type": "function_call_output",
                            "call_id": call["call_id"],
                            "output": serialized,
                        }
                    )
                request_body["input"] = conversation
                request_body["max_output_tokens"] = FINAL_OUTPUT_TOKENS
                if model in REASONING_MODELS:
                    request_body["reasoning"] = {"effort": "minimal"}
    except HTTPException as exc:
        yield _sse("error", {"message": str(exc.detail)})
        return
    except httpx.RequestError:
        yield _sse("error", {"message": "Could not reach the AI provider. Please try again."})
        return

    yield _sse("error", {"message": "The assistant used too many tool steps. Please narrow the request."})


def chat(db: Session, user: AppUser, payload: AssistantChatRequest) -> AssistantChatResponse:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CONTINUUM Copilot is not configured. Add OPENAI_API_KEY to Replit Secrets.",
        )

    if payload.model not in ALLOWED_MODELS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported assistant model")
    model = (
        _choose_auto_model(payload.message, payload.reasoning_effort)
        if payload.model == "auto"
        else payload.model
    )
    team_id = resolve_team_id(db, user, None)

    conversation: list[dict[str, Any]] = [
        {"role": "developer", "content": _system_prompt(user, team_id, payload.message)}
    ]
    conversation.extend(_compact_history(payload))
    conversation.append({"role": "user", "content": payload.message})

    request_body: dict[str, Any] = {
        "model": model,
        "input": conversation,
        "tools": available_tool_specs(user),
        "tool_choice": "auto",
        "max_output_tokens": INITIAL_OUTPUT_TOKENS,
    }
    if model in REASONING_MODELS:
        request_body["reasoning"] = {"effort": REASONING_MAP[payload.reasoning_effort]}

    activities: list[ToolActivity] = []
    pending_action = None
    answer_parts: list[str] = []
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        with httpx.Client(timeout=60.0) as client:
            for _ in range(8):
                response = _post_with_retry(client, headers, request_body)
                if response.status_code >= 400:
                    detail = "The AI provider could not complete this request."
                    try:
                        provider_error = response.json().get("error", {}).get("message")
                        if provider_error:
                            detail = provider_error
                    except ValueError:
                        pass
                    raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)

                result = response.json()
                output = result.get("output", [])
                if result.get("status") == "incomplete":
                    reason = result.get("incomplete_details", {}).get("reason")
                    if reason == "max_output_tokens" and request_body["max_output_tokens"] < MAX_OUTPUT_TOKENS:
                        partial = _extract_text(output)
                        if partial:
                            answer_parts.append(partial)
                            conversation.append({"role": "assistant", "content": partial})
                            conversation.append(
                                {
                                    "role": "developer",
                                    "content": "Continue exactly where the prior answer stopped without repeating it.",
                                }
                            )
                        request_body["input"] = conversation
                        request_body["max_output_tokens"] = min(
                            request_body["max_output_tokens"] * 2,
                            MAX_OUTPUT_TOKENS,
                        )
                        if model in REASONING_MODELS:
                            request_body["reasoning"] = {"effort": "minimal"}
                        continue
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Incomplete assistant response: {reason or 'unknown reason'}",
                    )
                calls = [item for item in output if item.get("type") == "function_call"]
                if not calls:
                    answer = _extract_text(output)
                    return AssistantChatResponse(
                        answer=("".join(answer_parts) + answer).strip()
                        or "I completed the request but did not receive a text response.",
                        model_used=model,
                        tool_activity=activities,
                        pending_action=pending_action,
                    )

                conversation.extend(output)
                for call in calls:
                    name = call.get("name", "")
                    try:
                        arguments = json.loads(call.get("arguments") or "{}")
                        tool_result, proposed_action = execute_tool(db, user, team_id, name, arguments)
                        if proposed_action is not None:
                            pending_action = proposed_action
                        serialized = _serialize_tool_result(tool_result)
                    except HTTPException as exc:
                        serialized = json.dumps({"error": exc.detail, "status_code": exc.status_code})
                    except (ValueError, TypeError, KeyError) as exc:
                        serialized = json.dumps({"error": f"Invalid tool input: {exc}"})
                    activities.append(ToolActivity(name=name, label=TOOL_LABELS.get(name, name)))
                    conversation.append(
                        {
                            "type": "function_call_output",
                            "call_id": call["call_id"],
                            "output": serialized,
                        }
                    )
                request_body["input"] = conversation
                request_body["max_output_tokens"] = FINAL_OUTPUT_TOKENS
                if model in REASONING_MODELS:
                    request_body["reasoning"] = {"effort": "minimal"}
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach the AI provider. Please try again.",
        ) from exc

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="The assistant used too many tool steps. Please narrow the request.",
    )
