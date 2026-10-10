from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from .agent import app


def main() -> None:
    config: RunnableConfig = {"configurable": {"thread_id": "weather-booking-demo"}}

    questions = [
        "What's the weather forecast in Teruel for October 11, 2026?",
        "Great! Book a hiking activity for 2 people on October 11, 2026.",
    ]

    for question in questions:
        print(f"\nUser: {question}")

        result = app.invoke(
            {"messages": [("user", question)]},
            config=config,
        )

        while "__interrupt__" in result:
            interruption = result["__interrupt__"][0].value

            print("\nBooking approval required:")
            print(f"Tool: {interruption['tool']}")
            print(f"Arguments: {interruption['arguments']}")

            answer = input("Approve booking? (yes/no): ")
            approved = answer.strip().lower() == "yes"

            result = app.invoke(
                Command(resume=approved),
                config=config,
            )

        print(f"Assistant: {result['messages'][-1].content}")


if __name__ == "__main__":
    main()
