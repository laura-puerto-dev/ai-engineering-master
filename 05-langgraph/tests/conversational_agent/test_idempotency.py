import json
from pathlib import Path

import pytest

import conversational_agent.tools as agent_tools
from conversational_agent.tools import create_reservation


def test_repeated_booking_does_not_create_duplicates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reservations_file = tmp_path / "reservations.json"

    monkeypatch.setattr(
        agent_tools,
        "RESERVATIONS_FILE",
        reservations_file,
    )

    booking_args = {
        "activity": "Hiking",
        "city": "Teruel",
        "booking_date": "2026-11-15",
        "people": 2,
        "idempotency_key": "conversation-123:call-456",
    }

    first_result = create_reservation(**booking_args)
    second_result = create_reservation(**booking_args)

    reservations = json.loads(reservations_file.read_text(encoding="utf-8"))

    assert first_result == second_result
    assert first_result["status"] == "confirmed"
    assert len(reservations) == 1
    assert reservations[0]["id"] == first_result["reservation"]["id"]


def test_same_idempotency_key_with_different_args_returns_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reservations_file = tmp_path / "reservations.json"

    monkeypatch.setattr(
        agent_tools,
        "RESERVATIONS_FILE",
        reservations_file,
    )

    booking_args = {
        "activity": "Hiking",
        "city": "Teruel",
        "booking_date": "2026-11-15",
        "people": 2,
        "idempotency_key": "conversation-123:call-456",
    }

    first_result = create_reservation(**booking_args)

    conflicting_args = {
        **booking_args,
        "activity": "Kayaking",
    }

    second_result = create_reservation(**conflicting_args)

    reservations = json.loads(reservations_file.read_text(encoding="utf-8"))

    assert first_result["status"] == "confirmed"
    assert second_result == {
        "error": "Idempotency key already used for a different booking."
    }
    assert len(reservations) == 1
    assert reservations[0]["activity"] == "Hiking"


def test_different_idempotency_keys_create_separate_bookings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reservations_file = tmp_path / "reservations.json"

    monkeypatch.setattr(
        agent_tools,
        "RESERVATIONS_FILE",
        reservations_file,
    )

    booking_args = {
        "activity": "Hiking",
        "city": "Teruel",
        "booking_date": "2026-11-15",
        "people": 2,
    }

    first_result = create_reservation(
        **booking_args,
        idempotency_key="conversation-123:call-456",
    )

    second_result = create_reservation(
        **booking_args,
        idempotency_key="conversation-123:call-789",
    )

    reservations = json.loads(reservations_file.read_text(encoding="utf-8"))

    assert first_result["status"] == "confirmed"
    assert second_result["status"] == "confirmed"
    assert first_result["reservation"]["id"] != second_result["reservation"]["id"]
    assert len(reservations) == 2
