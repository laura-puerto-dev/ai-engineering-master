from dotenv import load_dotenv

from evaluation.judge import evaluate_response

CALIBRATION_CASES = [
    {
        "id": "correct_shipping_policy",
        "description": "Correct answer grounded in company policy",
        "message": "¿Cuánto tarda en llegar un pedido nacional?",
        "category": "pregunta",
        "answer": (
            "Los pedidos nacionales tardan entre 2 y 4 días laborables "
            "desde la confirmación del pedido."
        ),
    },
    {
        "id": "invented_shipping_policy",
        "description": "Answer containing fabricated shipping policies",
        "message": "¿Cuánto tarda en llegar un pedido nacional?",
        "category": "pregunta",
        "answer": (
            "Todos los pedidos nacionales llegan en menos de 24 horas. "
            "Además, garantizamos el reembolso completo si se retrasan."
        ),
    },
    {
        "id": "correct_but_rude",
        "description": "Factually correct answer with an inappropriate tone",
        "message": "¿Cuánto tarda en llegar un pedido nacional?",
        "category": "pregunta",
        "answer": (
            "Los pedidos nacionales tardan entre 2 y 4 días laborables "
            "desde la confirmación del pedido. "
            "Deberías leer la información antes de hacer preguntas tan básicas."
        ),
    },
    {
        "id": "polite_but_irrelevant",
        "description": "Polite and grounded answer that misses the question",
        "message": "¿Cuánto tarda en llegar un pedido nacional?",
        "category": "pregunta",
        "answer": (
            "¡Gracias por contactar con NovaShop! "
            "Puedes devolver los productos dentro de los 30 días "
            "posteriores a su recepción. "
            "Estaremos encantados de ayudarte."
        ),
    },
    {
        "id": "mixed_supported_and_unsupported_claims",
        "description": "Empathetic and relevant answer mixing a valid policy with an invented exception",
        "message": "Llevo varios días intentando devolver un producto y nadie me ayuda.",
        "category": "queja",
        "answer": (
            "Siento mucho las dificultades que estás teniendo "
            "con la devolución. Entiendo tu frustración. "
            "Nuestra política permite solicitar devoluciones "
            "dentro de los 30 días posteriores a la recepción "
            "del pedido. Si ese plazo ya ha pasado, podemos "
            "ofrecerte una excepción y tramitar la devolución "
            "igualmente."
        ),
    },
]


def main() -> None:
    load_dotenv(".env")

    for case in CALIBRATION_CASES:
        print(f"\nCase: {case['id']}")
        print(f"Description: {case['description']}")

        evaluation = evaluate_response(
            message=case["message"],
            category=case["category"],
            answer=case["answer"],
        )

        print(evaluation.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
