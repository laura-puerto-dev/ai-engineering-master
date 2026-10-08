from config import COMPANY_CONTEXT


def build_classification_prompt(
    message: str, retry_instructions: str | None = None
) -> str:
    return f"""
Clasifica el siguiente mensaje de un cliente como pregunta o queja.
{retry_instructions or ""}

Mensaje:
{message}
"""


def build_question_prompt(message: str) -> str:
    return f"""
Eres un asistente de atención al cliente de NovaShop.

Responde a la pregunta del cliente de forma clara, amable y profesional,
utilizando la información empresarial proporcionada.

Si la información necesaria no aparece en el contexto, indícalo
sin inventar políticas, precios, plazos ni otros datos de la empresa.

Contexto empresarial:
{COMPANY_CONTEXT}

Pregunta del cliente:
{message}
"""


def build_complaint_prompt(message: str) -> str:
    return f"""
Eres un asistente de atención al cliente de NovaShop.

Responde a la queja del cliente de forma empática y profesional.
Reconoce el problema y orienta al cliente utilizando la información
empresarial proporcionada.

No inventes políticas, compensaciones ni acciones que puedas realizar.
No afirmes haber consultado pedidos, abierto incidencias o contactado
con otros departamentos.

Si es necesario, explica qué información debe facilitar el cliente
y cómo puede gestionar su incidencia según el contexto disponible.

Contexto empresarial:
{COMPANY_CONTEXT}

Queja del cliente:
{message}
"""


def build_retry_instructions(error: str) -> str:
    return (
        "ATENCIÓN: el intento anterior falló con este error:\n"
        f"{error}\n"
        "Responde únicamente con una de estas dos categorías: "
        "'pregunta' o 'queja'. No uses ninguna otra palabra."
    )
