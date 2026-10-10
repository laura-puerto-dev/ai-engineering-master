from unittest.mock import patch

from langchain_core.messages import AIMessage, ToolCall
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

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
