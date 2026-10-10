from unittest.mock import patch

import pytest
from langchain_core.messages import AIMessage, ToolCall, ToolMessage

from conversational_agent.agent import AgentState, authorization, execution


def test_rejected_booking_is_not_executed() -> None:
    rejected_call: ToolCall = {
        "name": "book_activity",
        "args": {
            "activity": "hiking",
            "city": "Teruel",
            "booking_date": "2026-10-11",
            "people": 2,
        },
        "id": "booking-123",
        "type": "tool_call",
    }

    state: AgentState = {
        "messages": [],
        "authorized_calls": [],
        "rejected_calls": [rejected_call],
    }

    with patch("conversational_agent.agent.tool_executor") as mock_executor:
        result = execution(state)

        mock_executor.invoke.assert_not_called()

    assert len(result["messages"]) == 1
    assert result["messages"][0].tool_call_id == "booking-123"
    assert "denied" in result["messages"][0].content


def test_authorized_booking_is_executed() -> None:
    authorized_call: ToolCall = {
        "name": "book_activity",
        "args": {
            "activity": "hiking",
            "city": "Teruel",
            "booking_date": "2026-10-11",
            "people": 2,
        },
        "id": "booking-456",
        "type": "tool_call",
    }

    state: AgentState = {
        "messages": [],
        "authorized_calls": [authorized_call],
        "rejected_calls": [],
    }

    tool_response = ToolMessage(
        content="Booking confirmed",
        tool_call_id="booking-456",
    )

    with patch("conversational_agent.agent.tool_executor") as mock_executor:
        mock_executor.invoke.return_value = {"messages": [tool_response]}

        result = execution(state)

        mock_executor.invoke.assert_called_once()

        invocation = mock_executor.invoke.call_args.args[0]
        executed_calls = invocation["messages"][0].tool_calls

        assert executed_calls == [authorized_call]
        assert result["messages"] == [tool_response]


def test_only_authorized_calls_are_executed() -> None:
    weather_call: ToolCall = {
        "name": "get_weather",
        "args": {
            "city": "Teruel",
            "forecast_date": "2026-10-11",
        },
        "id": "weather-123",
        "type": "tool_call",
    }

    booking_call: ToolCall = {
        "name": "book_activity",
        "args": {
            "activity": "hiking",
            "city": "Teruel",
            "booking_date": "2026-10-11",
            "people": 2,
        },
        "id": "booking-789",
        "type": "tool_call",
    }

    state: AgentState = {
        "messages": [],
        "authorized_calls": [weather_call],
        "rejected_calls": [booking_call],
    }

    weather_response = ToolMessage(
        content="Sunny",
        tool_call_id="weather-123",
    )

    with patch("conversational_agent.agent.tool_executor") as mock_executor:
        mock_executor.invoke.return_value = {"messages": [weather_response]}

        result = execution(state)

        mock_executor.invoke.assert_called_once()

        invocation = mock_executor.invoke.call_args.args[0]
        executed_calls = invocation["messages"][0].tool_calls

        assert executed_calls == [weather_call]

    assert len(result["messages"]) == 2
    assert result["messages"][0] == weather_response
    assert result["messages"][1].tool_call_id == "booking-789"
    assert "denied" in result["messages"][1].content


def test_weather_is_automatically_authorized() -> None:
    weather_call: ToolCall = {
        "name": "get_weather",
        "args": {
            "city": "Teruel",
            "forecast_date": "2026-10-11",
        },
        "id": "weather-456",
        "type": "tool_call",
    }

    state: AgentState = {
        "messages": [AIMessage(content="", tool_calls=[weather_call])],
    }

    result = authorization(state)

    assert result["authorized_calls"] == [weather_call]
    assert result["rejected_calls"] == []


@pytest.mark.parametrize("approved", [False, True])
def test_booking_requires_human_approval(approved: bool) -> None:
    booking_call: ToolCall = {
        "name": "book_activity",
        "args": {
            "activity": "hiking",
            "city": "Teruel",
            "booking_date": "2026-10-11",
            "people": 2,
        },
        "id": "booking-approval-123",
        "type": "tool_call",
    }

    state: AgentState = {
        "messages": [AIMessage(content="", tool_calls=[booking_call])],
    }

    with patch(
        "conversational_agent.agent.interrupt",
        return_value=approved,
    ) as mock_interrupt:
        result = authorization(state)

    mock_interrupt.assert_called_once_with(
        {
            "tool": "book_activity",
            "arguments": booking_call["args"],
            "tool_call_id": booking_call["id"],
            "message": "Do you approve this booking?",
        }
    )

    if approved:
        assert result["authorized_calls"] == [booking_call]
        assert result["rejected_calls"] == []
    else:
        assert result["authorized_calls"] == []
        assert result["rejected_calls"] == [booking_call]


def test_unknown_tool_is_rejected() -> None:
    unknown_call: ToolCall = {
        "name": "delete_all_reservations",
        "args": {},
        "id": "unknown-123",
        "type": "tool_call",
    }

    state: AgentState = {
        "messages": [AIMessage(content="", tool_calls=[unknown_call])],
    }

    with patch("conversational_agent.agent.interrupt") as mock_interrupt:
        result = authorization(state)

    mock_interrupt.assert_not_called()

    assert result["authorized_calls"] == []
    assert result["rejected_calls"] == [unknown_call]
