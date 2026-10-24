import os
import sqlite3
from unittest.mock import patch

from langchain_core.messages import AIMessage, ToolCall
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite import SqliteSaver

from conversational_agent.agent import builder


def main() -> None:
    booking_call: ToolCall = {
        "name": "book_activity",
        "args": {
            "activity": "hiking",
            "city": "Teruel",
            "booking_date": "2026-11-14",
            "people": 2,
        },
        "id": "checkpoint-test-booking",
        "type": "tool_call",
    }

    config: RunnableConfig = {
        "configurable": {"thread_id": "checkpoint-persistence-test"}
    }

    connection = sqlite3.connect(
        os.environ["TEST_CHECKPOINT_DB"],
        check_same_thread=False,
    )

    try:
        app = builder.compile(checkpointer=SqliteSaver(connection))

        with patch("conversational_agent.agent.llm_with_tools") as mock_llm:
            mock_llm.invoke.return_value = AIMessage(
                content="",
                tool_calls=[booking_call],
            )

            result = app.invoke(
                {"messages": [("user", "Book a hiking activity in Teruel.")]},
                config=config,
            )

        assert "__interrupt__" in result
        assert result["__interrupt__"][0].value["tool"] == "book_activity"

        print("Booking paused successfully.")

    finally:
        connection.close()


if __name__ == "__main__":
    main()
