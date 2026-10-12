from dotenv import load_dotenv
from langfuse import get_client


def main() -> None:
    load_dotenv()
    langfuse = get_client()

    prompt = langfuse.get_prompt(
        "novashop-classification",
        label="production",
    )

    compiled_prompt = prompt.compile(
        message="¿Cuánto tarda normalmente un envío?",
        retry_instructions="",
    )

    print(f"Prompt: {prompt.name}")
    print(f"Version: {prompt.version}")
    print(f"\nCompiled prompt:\n{compiled_prompt}")


if __name__ == "__main__":
    main()
