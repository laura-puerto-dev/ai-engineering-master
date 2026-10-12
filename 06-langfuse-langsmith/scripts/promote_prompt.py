"""Promote an existing NovaShop prompt version to production."""

import argparse

from dotenv import load_dotenv
from langfuse import get_client

PROMPT_NAME = "novashop-classification"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Promote a NovaShop prompt version to production."
    )

    parser.add_argument(
        "--version",
        type=int,
        required=True,
        help="Existing Langfuse prompt version to promote.",
    )

    parser.add_argument(
        "--promote",
        action="store_true",
        help="Explicitly confirm promotion to production.",
    )

    args = parser.parse_args()

    if not args.promote:
        parser.error("Use --promote to confirm the production change.")

    load_dotenv()
    langfuse = get_client()

    existing_prompts = langfuse.api.prompts.list(name=PROMPT_NAME)

    existing_prompt = next(
        (item for item in existing_prompts.data if item.name == PROMPT_NAME),
        None,
    )

    existing_versions = existing_prompt.versions if existing_prompt else []

    if args.version not in existing_versions:
        parser.error(
            f"Version {args.version} does not exist for '{PROMPT_NAME}'. "
            f"Available versions: {existing_versions}"
        )

    production_prompt = langfuse.get_prompt(
        PROMPT_NAME,
        label="production",
    )

    if production_prompt.version == args.version:
        print(f"Version {args.version} is already in production. Nothing to promote.")
        return

    updated_prompt = langfuse.api.prompt_version.update(
        name=PROMPT_NAME,
        version=args.version,
        new_labels=["production"],
    )

    print(
        f"Promoted '{updated_prompt.name}' "
        f"version {updated_prompt.version} to production."
    )


if __name__ == "__main__":
    main()
