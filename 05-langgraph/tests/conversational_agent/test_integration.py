import json
from pathlib import Path
from unittest.mock import patch

import pytest
from langchain_core.messages import AIMessage, ToolCall, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

import conversational_agent.tools as agent_tools
from conversational_agent.agent import builder

test_app = builder.compile(checkpointer=MemorySaver())


def test_rejected_booking_is_not_executed() -> None:
    booking_call: ToolCall = {
        "name": "book_activity",
        "args": {
            "activity": "hiking",
            "city": "Teruel",
            "booking_date": "2026-10-11",
            "people": 2,
        },
        "id": "booking-integration-123",
        "type": "tool_call",
    }

    llm_responses = [
        AIMessage(content="", tool_calls=[booking_call]),
        AIMessage(content="The booking was not completed."),
    ]

    test_app = builder.compile(checkpointer=MemorySaver())
    config: RunnableConfig = {"configurable": {"thread_id": "rejected-booking-test"}}

    with (
        patch("conversational_agent.agent.llm_with_tools") as mock_llm,
        patch("conversational_agent.agent.tool_executor") as mock_executor,
    ):
        mock_llm.invoke.side_effect = llm_responses

        # Start the conversation.
        result = test_app.invoke(
            {"messages": [("user", "Book a hiking activity in Teruel.")]},
            config=config,
        )

        # The graph must pause before executing the booking.
        assert "__interrupt__" in result

        interruption = result["__interrupt__"][0]
        details = interruption.value

        assert details["tool"] == "book_activity"
        assert details["arguments"] == booking_call["args"]
        assert details["tool_call_id"] == booking_call["id"]

        mock_executor.invoke.assert_not_called()

        # Simulate the user rejecting the booking.
        result = test_app.invoke(
            Command(resume=False),
            config=config,
        )

        # The booking must never reach the tool executor.
        mock_executor.invoke.assert_not_called()

    # The graph must finish without another interruption.
    assert "__interrupt__" not in result
    assert result["messages"][-1].content == "The booking was not completed."

    rejection_messages = [
        message
        for message in result["messages"]
        if isinstance(message, ToolMessage)
        and message.tool_call_id == booking_call["id"]
    ]

    assert len(rejection_messages) == 1


def test_rejected_booking_does_not_modify_reservations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reservations_file = tmp_path / "reservations.json"

    initial_reservations = [
        {
            "id": "RES-EXISTING",
            "activity": "Cycling",
            "city": "Teruel",
            "date": "2026-11-15",
            "people": 2,
        }
    ]

    reservations_file.write_text(
        json.dumps(initial_reservations),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        agent_tools,
        "RESERVATIONS_FILE",
        reservations_file,
    )

    booking_call: ToolCall = {
        "name": "book_activity",
        "args": {
            "activity": "Hiking",
            "city": "Teruel",
            "booking_date": "2026-11-15",
            "people": 2,
        },
        "id": "booking-persistence-test",
        "type": "tool_call",
    }

    llm_responses = [
        AIMessage(content="", tool_calls=[booking_call]),
        AIMessage(content="The booking was not completed."),
    ]

    test_app = builder.compile(checkpointer=MemorySaver())
    config: RunnableConfig = {
        "configurable": {"thread_id": "rejected-booking-persistence-test"}
    }

    with patch("conversational_agent.agent.llm_with_tools") as mock_llm:
        mock_llm.invoke.side_effect = llm_responses

        # Request the booking and wait for human approval.
        result = test_app.invoke(
            {"messages": [("user", "Book a hiking activity in Teruel.")]},
            config=config,
        )

        assert "__interrupt__" in result

        # Reject the booking and resume the workflow.
        result = test_app.invoke(
            Command(resume=False),
            config=config,
        )

    # The workflow must finish without another interruption.
    assert "__interrupt__" not in result

    # Rejected bookings must not change persisted reservations.
    persisted_reservations = json.loads(reservations_file.read_text(encoding="utf-8"))

    assert persisted_reservations == initial_reservations


def test_booking_is_idempotent_when_the_same_tool_call_id_runs_twice(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression test for a ToolNode behavior: it strips any caller-supplied
    value for a plain `InjectedToolArg` parameter and only refills args it
    knows how to compute itself (`InjectedState`, `InjectedStore`,
    `ToolRuntime`). The idempotency key must therefore be derived inside
    `book_activity` from `ToolRuntime`, not pushed into `tool_call["args"]`
    by the graph. This drives two full approve-and-execute cycles with the
    same tool_call id on the same thread and checks the booking only happens
    once.
    """
    reservations_file = tmp_path / "reservations.json"

    monkeypatch.setattr(
        agent_tools,
        "RESERVATIONS_FILE",
        reservations_file,
    )

    booking_call: ToolCall = {
        "name": "book_activity",
        "args": {
            "activity": "Hiking",
            "city": "Teruel",
            "booking_date": "2026-11-15",
            "people": 2,
        },
        "id": "idempotency-regression-test",
        "type": "tool_call",
    }

    llm_responses = [
        AIMessage(content="", tool_calls=[booking_call]),
        AIMessage(content="Booking confirmed once."),
        AIMessage(content="", tool_calls=[booking_call]),
        AIMessage(content="Booking confirmed twice."),
    ]

    test_app = builder.compile(checkpointer=MemorySaver())
    config: RunnableConfig = {
        "configurable": {"thread_id": "idempotency-regression-test"}
    }

    with patch("conversational_agent.agent.llm_with_tools") as mock_llm:
        mock_llm.invoke.side_effect = llm_responses

        test_app.invoke(
            {"messages": [("user", "Book a hiking activity in Teruel.")]},
            config=config,
        )
        test_app.invoke(Command(resume=True), config=config)

        test_app.invoke(
            {"messages": [("user", "Book it again, same details.")]},
            config=config,
        )
        result = test_app.invoke(Command(resume=True), config=config)

    booking_messages = [
        message
        for message in result["messages"]
        if isinstance(message, ToolMessage)
        and message.tool_call_id == booking_call["id"]
    ]

    assert len(booking_messages) == 2
    assert all(message.status == "success" for message in booking_messages)
    assert booking_messages[0].content == booking_messages[1].content

    reservations = json.loads(reservations_file.read_text(encoding="utf-8"))

    assert len(reservations) == 1


def test_booking_result_does_not_expose_idempotency_key_to_the_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`idempotency_key` is an internal dedup detail. The tool must not include
    it in the result it hands back to the model (via the ToolMessage content),
    even though it is still persisted in the reservations file.
    """
    reservations_file = tmp_path / "reservations.json"

    monkeypatch.setattr(
        agent_tools,
        "RESERVATIONS_FILE",
        reservations_file,
    )

    booking_call: ToolCall = {
        "name": "book_activity",
        "args": {
            "activity": "Hiking",
            "city": "Teruel",
            "booking_date": "2026-11-15",
            "people": 2,
        },
        "id": "no-leak-test",
        "type": "tool_call",
    }

    llm_responses = [
        AIMessage(content="", tool_calls=[booking_call]),
        AIMessage(content="Booking confirmed."),
    ]

    test_app = builder.compile(checkpointer=MemorySaver())
    config: RunnableConfig = {"configurable": {"thread_id": "no-leak-test"}}

    with patch("conversational_agent.agent.llm_with_tools") as mock_llm:
        mock_llm.invoke.side_effect = llm_responses

        test_app.invoke(
            {"messages": [("user", "Book a hiking activity in Teruel.")]},
            config=config,
        )
        result = test_app.invoke(Command(resume=True), config=config)

    booking_message = next(
        message
        for message in result["messages"]
        if isinstance(message, ToolMessage)
        and message.tool_call_id == booking_call["id"]
    )

    assert booking_message.status == "success"
    assert "idempotency_key" not in booking_message.content

    # The dedup key must still be persisted, even though it is hidden from the model.
    reservations = json.loads(reservations_file.read_text(encoding="utf-8"))

    assert "idempotency_key" in reservations[0]


def test_booking_idempotency_key_is_scoped_to_the_thread(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The idempotency key combines thread_id and tool_call_id, so reusing
    the same tool_call id across different conversations must not collide.
    """
    reservations_file = tmp_path / "reservations.json"

    monkeypatch.setattr(
        agent_tools,
        "RESERVATIONS_FILE",
        reservations_file,
    )

    booking_call: ToolCall = {
        "name": "book_activity",
        "args": {
            "activity": "Hiking",
            "city": "Teruel",
            "booking_date": "2026-11-15",
            "people": 2,
        },
        "id": "shared-tool-call-id",
        "type": "tool_call",
    }

    for thread_id in ("thread-a", "thread-b"):
        llm_responses = [
            AIMessage(content="", tool_calls=[booking_call]),
            AIMessage(content="Booking confirmed."),
        ]

        test_app = builder.compile(checkpointer=MemorySaver())
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}

        with patch("conversational_agent.agent.llm_with_tools") as mock_llm:
            mock_llm.invoke.side_effect = llm_responses

            test_app.invoke(
                {"messages": [("user", "Book a hiking activity in Teruel.")]},
                config=config,
            )
            test_app.invoke(Command(resume=True), config=config)

    reservations = json.loads(reservations_file.read_text(encoding="utf-8"))

    assert len(reservations) == 2
    assert reservations[0]["idempotency_key"] != reservations[1]["idempotency_key"]
