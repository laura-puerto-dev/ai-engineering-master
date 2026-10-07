import csv
import warnings
from pathlib import Path

from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import BaseMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig, RunnableLambda
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.tools import tool
from langchain_ollama import ChatOllama

warnings.filterwarnings(
    "ignore"
)  # ocultamos el aviso de deprecación (ya lo vimos en el paso 4)

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "Eres un asistente de una tienda de productos electrónicos. Responde en español y en una o dos frases. "
                "Cuando consultes un producto con find_product, usa el resultado obtenido tal cual: no vuelvas a llamar "
                "a la tool con variantes del mismo nombre (por ejemplo añadiendo adjetivos como 'inalámbricos') para "
                "comprobar o comparar productos; si necesitas comparar, hazlo con los datos que ya tienes."
            ),
        ),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{question}"),
        # guarda la llamada a la tool y su resultado para que el modelo los vea antes de dar la respuesta final
        MessagesPlaceholder(variable_name="scratchpad", optional=True),
    ]
)


@tool
def find_product(product_name: str):
    """Look up a product by its exact name (e.g. 'Teclado', 'Ratón', 'Monitor',
    'Webcam', 'Auriculares') in the store catalog. The match is case-insensitive
    but exact - do not invent variants or add descriptive words if a lookup
    already succeeded; just use the result you got."""

    CATALOG_PATH = Path(__file__).with_name("products.csv")
    column = "producto"

    try:
        with CATALOG_PATH.open(newline="", encoding="utf-8") as file:
            for row in csv.DictReader(file):
                if row.get(column, "").strip().lower() == product_name.strip().lower():
                    return row
    except FileNotFoundError:
        return f"File '{CATALOG_PATH}' not found."
    return f"Product '{product_name}' does not exist."


tools = [find_product]
tools_by_name = {tool.name: tool for tool in tools}

model = ChatOllama(model="llama3.1", temperature=0)
model_with_tools = model.bind_tools(tools=tools)

chain = prompt | model_with_tools

histories: dict[str, InMemoryChatMessageHistory] = {}


def get_history(session_id: str) -> InMemoryChatMessageHistory:
    # almacén en memoria por sesión; no persiste entre ejecuciones del script
    if session_id not in histories:
        histories[session_id] = InMemoryChatMessageHistory()
    return histories[session_id]


def run_turn(inputs: dict) -> list[BaseMessage]:
    # bucle manual tipo ReAct (en vez de AgentExecutor): repite invoke -> tool
    # calls hasta que el modelo responda sin tool_calls, o se agote el límite
    # de seguridad (evita un bucle infinito si el modelo no deja de pedir tools)
    new_messages: list[BaseMessage] = []
    max_iterations = 5

    for _ in range(max_iterations):
        ai_response = chain.invoke(
            {
                "history": inputs["history"],
                "question": inputs["question"],
                "scratchpad": new_messages,
            }
        )
        new_messages.append(ai_response)

        if not ai_response.tool_calls:
            break

        for tool_call in ai_response.tool_calls:
            result = tools_by_name[tool_call["name"]].invoke(tool_call["args"])
            print(
                f"   TOOL CALL -> {tool_call['name']}({tool_call['args']}) -> {result}"
            )
            new_messages.append(
                ToolMessage(content=str(result), tool_call_id=tool_call["id"])
            )

    return new_messages


chat = RunnableWithMessageHistory(
    RunnableLambda(run_turn),
    get_history,
    input_messages_key="question",
    history_messages_key="history",
)


def main() -> None:
    config: RunnableConfig = {"configurable": {"session_id": "user-1"}}

    turns = [
        "Hola, puedes consultar el precio y stock del teclado?",
        "Ahora consulta por favor los auriculares y dime cuál de los dos es más barato",
    ]

    for i, question in enumerate(turns, 1):
        print(f"[Turno {i}] Tú  : {question}")
        new_messages = chat.invoke({"question": question}, config=config)
        print(f"[Turno {i}] Bot : {new_messages[-1].content}\n")


if __name__ == "__main__":
    main()
