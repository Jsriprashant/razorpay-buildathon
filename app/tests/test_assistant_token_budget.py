import json

from app.schemas.assistant import AssistantChatRequest, AssistantMessage
from app.services.assistant_service import (
    MAX_HISTORY_CHARS,
    MAX_TOOL_RESULT_ITEMS,
    _compact_history,
    _serialize_tool_result,
)
from app.models import AppUser, Role
from app.schemas.assistant import AssistantChatRequest
from app.services import assistant_service


def test_history_compaction_keeps_newest_messages_within_budget():
    payload = AssistantChatRequest(
        message="What changed?",
        history=[
            AssistantMessage(role="user", content="a" * 12_000),
            AssistantMessage(role="assistant", content="b" * 12_000),
            AssistantMessage(role="user", content="c" * 12_000),
        ],
    )

    compacted = _compact_history(payload)

    assert sum(len(item["content"]) for item in compacted) == MAX_HISTORY_CHARS
    assert compacted[-1] == {"role": "user", "content": "c" * 12_000}
    assert compacted[0] == {"role": "assistant", "content": "b" * 12_000}


def test_tool_result_serialization_bounds_large_lists_and_reports_total():
    serialized = _serialize_tool_result({"workers": [{"id": index} for index in range(80)]})
    result = json.loads(serialized)

    assert len(result["workers"]) == MAX_TOOL_RESULT_ITEMS + 1
    assert result["workers"][-1] == {
        "_truncated": True,
        "_returned_items": MAX_TOOL_RESULT_ITEMS,
        "_total_items": 80,
    }

def _user() -> AppUser:
    return AppUser(
        id=1,
        name="Test Manager",
        email="manager@example.test",
        role=Role.MANAGER,
        team_id=1,
    )

def test_interrupted_provider_stream_emits_error_not_done(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(assistant_service.httpx, "Client", _Client)
    monkeypatch.setattr(assistant_service, "resolve_team_id", lambda db, user, team_id: 1)

    def interrupted_stream(client, headers, request_body):
        yield {"type": "response.output_text.delta", "delta": "Partial answer"}

    monkeypatch.setattr(assistant_service, "_stream_provider_response", interrupted_stream)

    events = _events(
        list(
            assistant_service.chat_stream(
                object(),
                _user(),
                AssistantChatRequest(message="Write a long report", model="gpt-4.1-mini"),
            )
        )
    )

    assert ("answer_delta", {"delta": "Partial answer"}) in events
    assert events[-1] == (
        "error",
        {"message": "The assistant stream ended unexpectedly. Please try again."},
    )
    assert all(event != "done" for event, _ in events)

class _Client:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

def _events(frames: list[str]) -> list[tuple[str, dict]]:
    parsed = []
    for frame in frames:
        lines = frame.strip().splitlines()
        event = next(line[7:] for line in lines if line.startswith("event: "))
        data = json.loads(next(line[6:] for line in lines if line.startswith("data: ")))
        parsed.append((event, data))
    return parsed

def test_stream_continues_after_token_limit_without_repeating_text_or_tool(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(assistant_service.httpx, "Client", _Client)
    monkeypatch.setattr(assistant_service, "resolve_team_id", lambda db, user, team_id: 1)

    provider_calls = []
    provider_sequences = [
        [
            {
                "type": "response.completed",
                "response": {
                    "output": [
                        {
                            "type": "function_call",
                            "name": "get_roster",
                            "call_id": "call-1",
                            "arguments": "{}",
                        }
                    ]
                },
            }
        ],
        [
            {"type": "response.output_text.delta", "delta": "First half. "},
            {
                "type": "response.incomplete",
                "response": {
                    "output": [
                        {
                            "type": "message",
                            "content": [{"type": "output_text", "text": "First half. "}],
                        }
                    ],
                    "incomplete_details": {"reason": "max_output_tokens"},
                },
            },
        ],
        [
            {"type": "response.output_text.delta", "delta": "Second half."},
            {
                "type": "response.completed",
                "response": {
                    "output": [
                        {
                            "type": "message",
                            "content": [{"type": "output_text", "text": "Second half."}],
                        }
                    ]
                },
            },
        ],
    ]

    def stream_provider(client, headers, request_body):
        provider_calls.append(
            {
                "input": list(request_body["input"]),
                "max_output_tokens": request_body["max_output_tokens"],
            }
        )
        yield from provider_sequences[len(provider_calls) - 1]

    executed_tools = []

    def execute_tool(db, user, team_id, name, arguments):
        executed_tools.append((name, arguments))
        return [{"id": 1, "name": "Ada"}], None

    monkeypatch.setattr(assistant_service, "_stream_provider_response", stream_provider)
    monkeypatch.setattr(assistant_service, "execute_tool", execute_tool)

    events = _events(
        list(
            assistant_service.chat_stream(
                object(),
                _user(),
                AssistantChatRequest(message="Summarize the roster", model="gpt-4.1-mini"),
            )
        )
    )

    answer_deltas = [data["delta"] for event, data in events if event == "answer_delta"]
    done_events = [data for event, data in events if event == "done"]

    assert answer_deltas == ["First half. ", "Second half."]
    assert len(done_events) == 1
    assert done_events[0]["answer"] == "First half. Second half."
    assert events[-1][0] == "done"
    assert executed_tools == [("get_roster", {})]
    assert len(provider_calls) == 3
    assert provider_calls[2]["max_output_tokens"] == assistant_service.MAX_OUTPUT_TOKENS
    assert {"role": "assistant", "content": "First half."} in provider_calls[2]["input"]
