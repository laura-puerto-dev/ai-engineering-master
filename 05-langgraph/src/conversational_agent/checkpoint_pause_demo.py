from langchain_core.runnables import RunnableConfig

from conversational_agent.agent import app


def main() -> None:
    config: RunnableConfig = {
        "configurable": {
            "thread_id": "checkpoint-recovery-test",
        }
    }

    result = app.invoke(
        {
            "messages": [
                (
                    "user",
                    "Book a hiking activity in Teruel for 2 people on November 14, 2026.",
                )
            ]
        },
        config=config,
    )

    if "__interrupt__" not in result:
        raise RuntimeError("Expected a booking approval interruption.")

    interruption = result["__interrupt__"][0].value

    print("Booking paused successfully.")
    print(f"Tool: {interruption['tool']}")
    print(f"Arguments: {interruption['arguments']}")
    print("Python will now exit without approving the booking.")


if __name__ == "__main__":
    main()
