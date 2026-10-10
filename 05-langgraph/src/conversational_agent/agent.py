from typing import Annotated, NotRequired, TypedDict

from langchain_core.messages import AIMessage, ToolCall, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import Command, interrupt

from conversational_agent.tools import book_activity, get_weather


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    authorized_calls: NotRequired[list[ToolCall]]
    rejected_calls: NotRequired[list[ToolCall]]


tools = [get_weather, book_activity]

llm = ChatOllama(
    model="llama3.1",
    temperature=0,
)

llm_with_tools = llm.bind_tools(tools)


def assistant(state: AgentState):
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}


def authorization(state: AgentState):
    last_message = state["messages"][-1]

    if not isinstance(last_message, AIMessage):
        raise TypeError("Expected an AI message.")

    authorized_calls: list[ToolCall] = []
    rejected_calls: list[ToolCall] = []

    for tool_call in last_message.tool_calls:
        if tool_call["name"] == "get_weather":
            authorized_calls.append(tool_call)

        elif tool_call["name"] == "book_activity":
            approved = interrupt(
                {
                    "tool": tool_call["name"],
                    "arguments": tool_call["args"],
                    "tool_call_id": tool_call["id"],
                    "message": "Do you approve this booking?",
                }
            )

            if approved is True:
                authorized_calls.append(tool_call)
            else:
                rejected_calls.append(tool_call)

        else:
            rejected_calls.append(tool_call)

    return {
        "authorized_calls": authorized_calls,
        "rejected_calls": rejected_calls,
    }


tool_executor = ToolNode([get_weather, book_activity])


def execution(state: AgentState):
    authorized_calls = state.get("authorized_calls", [])
    rejected_calls = state.get("rejected_calls", [])

    results = []

    if authorized_calls:
        authorized_message = AIMessage(
            content="",
            tool_calls=authorized_calls,
        )

        tool_result = tool_executor.invoke({"messages": [authorized_message]})

        results.extend(tool_result["messages"])

    for tool_call in rejected_calls:
        results.append(
            ToolMessage(
                content="Tool execution denied: authorization was not granted.",
                tool_call_id=tool_call["id"],
                name=tool_call["name"],
            )
        )

    return {"messages": results}


def route_after_assistant(state: AgentState) -> str:
    last_message = state["messages"][-1]

    if not isinstance(last_message, AIMessage):
        raise TypeError("Expected an AI message.")

    if last_message.tool_calls:
        return "authorization"

    return "end"


builder = StateGraph(AgentState)

builder.add_node("assistant", assistant)
builder.add_node("authorization", authorization)
builder.add_node("execution", execution)

builder.add_edge(START, "assistant")

builder.add_conditional_edges(
    "assistant",
    route_after_assistant,
    {
        "authorization": "authorization",
        "end": END,
    },
)

builder.add_edge("authorization", "execution")
builder.add_edge("execution", "assistant")

memory = MemorySaver()
app = builder.compile(checkpointer=memory)


if __name__ == "__main__":
    config: RunnableConfig = {"configurable": {"thread_id": "booking-test-2"}}

    result = app.invoke(
        {
            "messages": [
                (
                    "user",
                    "Book a hiking activity in Teruel for 2 people on October 11, 2026.",
                )
            ]
        },
        config=config,
    )

    while result.get("__interrupt__"):
        interruption = result["__interrupt__"][0]
        details = interruption.value

        print("\nBooking approval required")
        print(f"Tool: {details['tool']}")
        print(f"Arguments: {details['arguments']}")

        answer = input("\nDo you approve? (yes/no): ").strip().lower()

        approved = answer == "yes"

        result = app.invoke(
            Command(resume=approved),
            config=config,
        )

    print("\nAssistant:", result["messages"][-1].content)
