from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from conversational_agent.agent import app


def main() -> None:
    config: RunnableConfig = {
        "configurable": {
            "thread_id": "checkpoint-recovery-test",
        }
    }

    # Recover the pending interruption without starting a new request.
    snapshot = app.get_state(config)

    if not snapshot.interrupts:
        raise RuntimeError("No pending approval found in the checkpoint.")

    interruption = snapshot.interrupts[0].value

    print("Pending booking recovered.")
    print(f"Tool: {interruption['tool']}")
    print(f"Arguments: {interruption['arguments']}")

    # Resume the interrupted workflow with explicit approval.
    result = app.invoke(Command(resume=True), config=config)

    if "__interrupt__" in result:
        raise RuntimeError("Workflow interrupted again unexpectedly.")

    print("Workflow resumed successfully.")
    print(f"Assistant: {result['messages'][-1].content}")


if __name__ == "__main__":
    main()
