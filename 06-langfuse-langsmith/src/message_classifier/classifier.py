from enum import Enum
from typing import TypedDict

from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langfuse import get_client
from langfuse.langchain import CallbackHandler
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from message_classifier.config import (
    MAX_ATTEMPTS,
    MODEL_NAME,
    MODEL_TEMPERATURE,
    SIMULATED_FAILURES,
    TEST_MESSAGE,
    TRACE_NAME,
)
from message_classifier.prompts import (
    build_complaint_prompt,
    build_question_prompt,
    build_retry_instructions,
)

load_dotenv()


class Category(str, Enum):
    QUESTION = "pregunta"
    COMPLAINT = "queja"


class Classification(BaseModel):
    category: Category = Field(
        description="Tipo de mensaje del cliente: pregunta o queja"
    )


class State(TypedDict):
    message: str
    category: Category | None
    answer: str
    classification_attempts: int
    classification_error: str | None
    retry_instructions: str | None


llm = ChatOllama(
    model=MODEL_NAME,
    temperature=MODEL_TEMPERATURE,
)

llm_classifier = llm.with_structured_output(Classification)


def classify(
    state: State,
    config: RunnableConfig | None = None,
    prompt_version: int | None = None,
):
    if prompt_version is None and config is not None:
        prompt_version = config.get("configurable", {}).get(
            "classification_prompt_version"
        )
    instructions = state.get("retry_instructions") or ""

    langfuse = get_client()

    if prompt_version is None:
        classification_prompt = langfuse.get_prompt(
            "novashop-classification",
            label="production",
        )
    else:
        classification_prompt = langfuse.get_prompt(
            "novashop-classification",
            version=prompt_version,
        )

    prompt_template = PromptTemplate.from_template(
        classification_prompt.get_langchain_prompt(),
        metadata={"langfuse_prompt": classification_prompt},
    )

    try:
        # Simulate classification failures to test retry and error-handling paths.
        if state["classification_attempts"] < SIMULATED_FAILURES:
            raise ValueError("Fallo simulado: el modelo devolvió 'consulta'")

        result = (prompt_template | llm_classifier).invoke(
            {
                "retry_instructions": instructions,
                "message": state["message"],
            }
        )
        if not isinstance(result, Classification):
            raise TypeError(f"Salida inesperada del clasificador: {result!r}")
        return {
            "category": result.category,
            "classification_attempts": state["classification_attempts"] + 1,
            "classification_error": None,
        }
    except (ValueError, TypeError) as e:
        return {
            "category": None,
            "classification_attempts": state["classification_attempts"] + 1,
            "classification_error": str(e),
        }


def answer_question(state: State):
    prompt = build_question_prompt(message=state["message"])
    answer = llm.invoke(prompt)
    return {"answer": answer.content}


def respond_to_complaint(state: State):
    prompt = build_complaint_prompt(message=state["message"])
    answer = llm.invoke(prompt)
    return {"answer": answer.content}


def handle_error(state: State):
    return {
        "answer": (
            "No he podido clasificar correctamente el mensaje "
            "después de varios intentos."
        )
    }


def prepare_retry(state: State):
    error = (state["classification_error"] or "")[:500]
    # Feed the previous error back into the state to guide the next classification attempt.
    return {"retry_instructions": build_retry_instructions(error=error)}


def decide_branch(state: State):
    if state["category"] == Category.QUESTION:
        return "question"

    if state["category"] == Category.COMPLAINT:
        return "complaint"

    # Retry only while the maximum number of classification attempts has not been reached.
    if state["classification_attempts"] < MAX_ATTEMPTS:
        return "retry"

    return "error"


builder = StateGraph(State)

builder.add_node("classify", classify)
builder.add_node("prepare_retry", prepare_retry)
builder.add_node("answer_question", answer_question)
builder.add_node("respond_to_complaint", respond_to_complaint)
builder.add_node("handle_error", handle_error)

builder.add_edge(START, "classify")
builder.add_conditional_edges(
    "classify",
    decide_branch,
    {
        "question": "answer_question",
        "complaint": "respond_to_complaint",
        "retry": "prepare_retry",
        "error": "handle_error",
    },
)
builder.add_edge("prepare_retry", "classify")
builder.add_edge("answer_question", END)
builder.add_edge("respond_to_complaint", END)
builder.add_edge("handle_error", END)

app = builder.compile()

if __name__ == "__main__":
    initial_state: State = {
        "message": TEST_MESSAGE,
        "category": None,
        "answer": "",
        "classification_attempts": 0,
        "classification_error": None,
        "retry_instructions": None,
    }

    langfuse_handler = CallbackHandler()

    print("\n--- MESSAGE CLASSIFIER ---")
    print(f"\nMessage: {initial_state['message']}\n")

    for step in app.stream(
        initial_state,
        stream_mode="updates",
        config={
            "callbacks": [langfuse_handler],
            "run_name": TRACE_NAME,
        },
    ):
        for node_name, update in step.items():
            print(f"[NODE] {node_name}")

            if "category" in update:
                category = update["category"]
                if category is not None:
                    print(f"Category: {category.value}")

                print(f"Attempts: {update['classification_attempts']}")

            if update.get("classification_error"):
                print(f"Error: {update['classification_error']}")

            if "answer" in update:
                print(f"\n--- RESPONSE ---\n\n{update['answer']}")

            print()

    print("--- END ---")
