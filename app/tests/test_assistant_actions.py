import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import AppUser, AssistantActionGrant, Role
from app.schemas.assistant import AssistantActionResponse, PendingAction
from app.services.assistant_tools import (
    _claim_action,
    _sign_action,
    _store_action_result,
    _verify_action,
)
from datetime import datetime


def _user(user_id: int = 1) -> AppUser:
    return AppUser(
        id=user_id,
        name="Test Manager",
        email=f"manager-{user_id}@example.test",
        role=Role.MANAGER,
        team_id=1,
    )


def _action() -> PendingAction:
    return PendingAction(
        kind="submit_hiring_request",
        title="Submit request #5",
        description="Send the request to HR.",
        payload={"request_id": 5},
    )


def test_signed_action_round_trip_uses_server_payload(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    signed = _sign_action(_action(), _user(), 1, "one-time-nonce")
    browser_tampered = signed.model_copy(update={"payload": {"request_id": 999}})

    verified, nonce = _verify_action(browser_tampered, _user(), 1)

    assert verified.payload == {"request_id": 5}
    assert verified.confirmation_token is None
    assert nonce == "one-time-nonce"


def test_action_token_is_bound_to_user_and_team(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    signed = _sign_action(_action(), _user(), 1, "one-time-nonce")

    with pytest.raises(HTTPException) as wrong_user:
        _verify_action(signed, _user(2), 1)
    assert wrong_user.value.status_code == 403

    with pytest.raises(HTTPException) as wrong_team:
        _verify_action(signed, _user(), 2)
    assert wrong_team.value.status_code == 403


def test_invalid_action_token_never_reaches_mutation(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    invalid = _action().model_copy(update={"confirmation_token": "not-a-valid-token"})

    with pytest.raises(HTTPException) as exc:
        _verify_action(invalid, _user(), 1)

    assert exc.value.status_code == 400


def test_action_grant_is_one_time_and_replays_return_same_result():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    AssistantActionGrant.__table__.create(engine)
    with Session(engine) as db:
        db.add(
            AssistantActionGrant(
                id="single-use",
                user_id=1,
                team_id=1,
                action_kind="submit_hiring_request",
                created_at=datetime.utcnow(),
            )
        )
        db.commit()

        assert _claim_action(db, "single-use", _user(), 1) is None
        with pytest.raises(HTTPException) as in_progress:
            _claim_action(db, "single-use", _user(), 1)
        assert in_progress.value.status_code == 409

        expected = AssistantActionResponse(message="Submitted", link="/requests/5", entity_id=5)
        _store_action_result(db, "single-use", expected)
        replay = _claim_action(db, "single-use", _user(), 1)

        assert replay == expected