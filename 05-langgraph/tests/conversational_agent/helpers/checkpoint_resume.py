import json
import os
import sqlite3
from pathlib import Path
from unittest.mock import patch

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from conversational_agent.agent import builder


def main() -> None:
    config: RunnableConfig = {
        "configurable": {"thread_id": "checkpoint-persistence-test"}
    }

    reservations_file = Path(os.environ["TEST_RESERVATIONS_FILE"])

    connection = sqlite3.connect(
        os.environ["TEST_CHECKPOINT_DB"],
        check_same_thread=False,
    )

    try:
        app = builder.compile(checkpointer=SqliteSaver(connection))

        snapshot = app.get_state(config)

        assert snapshot.interrupts
        assert snapshot.interrupts[0].value["tool"] == "book_activity"

        with (
            patch("conversational_agent.agent.llm_with_tools") as mock_llm,
            patch(
                "conversational_agent.tools.RESERVATIONS_FILE",
                reservations_file,
            ),
        ):
            mock_llm.invoke.return_value = AIMessage(
                content="The booking has been completed."
            )

            result = app.invoke(Command(resume=True), config=config)

        assert "__interrupt__" not in result
        assert result["messages"][-1].content == ("The booking has been completed.")

        reservations = json.loads(reservations_file.read_text(encoding="utf-8"))

        assert len(reservations) == 1
        assert reservations[0]["activity"] == "hiking"
        assert reservations[0]["city"] == "Teruel"
        assert reservations[0]["date"] == "2026-11-14"
        assert reservations[0]["people"] == 2

        print("Checkpoint recovered and booking executed successfully.")

    finally:
        connection.close()


if __name__ == "__main__":
    main()
