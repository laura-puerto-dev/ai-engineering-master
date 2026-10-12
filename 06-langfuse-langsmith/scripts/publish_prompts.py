"""Publish NovaShop prompts to Langfuse."""

import argparse

from dotenv import load_dotenv
from langfuse import get_client

PROMPT_NAME = "novashop-classification"

CLASSIFICATION_PROMPT_V1 = """
Clasifica el siguiente mensaje de un cliente como pregunta o queja.
{{retry_instructions}}

Mensaje:
{{message}}
"""

CLASSIFICATION_PROMPT_V2 = """
Clasifica el siguiente mensaje de un cliente como pregunta o queja.

Criterios de clasificación:
- Clasifica como "queja" cuando el cliente describa un problema real
  con un pedido, producto o servicio de NovaShop, aunque formule
  el mensaje como una pregunta.
- Clasifica como "pregunta" cuando solicite información general
  o plantee una situación hipotética.
- Si menciona una experiencia negativa con otra empresa,
  no la consideres una queja contra NovaShop.

{{retry_instructions}}

Mensaje:
{{message}}
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Publish the NovaShop classification prompt to Langfuse."
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Confirm creation of a new prompt version.",
    )

    parser.add_argument(
        "--version",
        type=int,
        choices=[1, 2],
        required=True,
        help="Prompt version to publish (1 or 2).",
    )
    args = parser.parse_args()

    if not args.publish:
        parser.error("Use --publish to explicitly create a new prompt version.")

    prompt_versions = {
        1: CLASSIFICATION_PROMPT_V1,
        2: CLASSIFICATION_PROMPT_V2,
    }

    selected_prompt = prompt_versions[args.version]

    load_dotenv()
    langfuse = get_client()

    existing_prompts = langfuse.api.prompts.list(name=PROMPT_NAME)

    existing_prompt = next(
        (item for item in existing_prompts.data if item.name == PROMPT_NAME),
        None,
    )

    existing_versions = existing_prompt.versions if existing_prompt else []

    for version in existing_versions:
        existing_prompt_version = langfuse.api.prompts.get(
            PROMPT_NAME,
            version=version,
        )

        if existing_prompt_version.prompt == selected_prompt:
            print(
                f"Prompt content already exists in Langfuse "
                f"(version {version}). Nothing to publish."
            )
            return

    if not existing_versions and args.version != 1:
        parser.error("The first published prompt must use template v1.")

    prompt = langfuse.create_prompt(
        name=PROMPT_NAME,
        prompt=selected_prompt,
        labels=["production"] if not existing_versions else [],
        commit_message=f"Template v{args.version}: NovaShop classification prompt",
    )

    langfuse.flush()

    print(f"Published '{prompt.name}' version {prompt.version}")


if __name__ == "__main__":
    main()
