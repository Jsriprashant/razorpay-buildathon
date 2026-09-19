import json

from app.schemas.assistant import AssistantChatRequest, AssistantMessage
from app.services.assistant_service import (
    MAX_HISTORY_CHARS,
    MAX_TOOL_RESULT_ITEMS,
    _compact_history,
    _serialize_tool_result,
)


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