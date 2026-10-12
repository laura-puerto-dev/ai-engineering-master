import argparse
import hashlib
import json
from pathlib import Path

from dotenv import load_dotenv
from langfuse import get_client
from message_classifier.classifier import State, classify
from message_classifier.config import MODEL_NAME, MODEL_TEMPERATURE

DATASET_PATH = (
    Path(__file__).resolve().parents[2] / "datasets" / "message_classification.jsonl"
)


def load_dataset() -> list[dict]:
    with DATASET_PATH.open(encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def evaluate_classification(prompt_version: int) -> None:
    load_dotenv()
    langfuse = get_client()

    existing_prompts = langfuse.api.prompts.list(name="novashop-classification")

    existing_prompt = next(
        (
            item
            for item in existing_prompts.data
            if item.name == "novashop-classification"
        ),
        None,
    )

    if existing_prompt is None:
        raise ValueError("Prompt 'novashop-classification' does not exist.")

    if prompt_version not in existing_prompt.versions:
        raise ValueError(
            f"Version {prompt_version} does not exist for "
            f"'novashop-classification'. "
            f"Available versions: {existing_prompt.versions}"
        )

    experiment_name = f"classification_v{prompt_version}"

    output_path = (
        Path(__file__).resolve().parents[2] / "results" / f"{experiment_name}.json"
    )

    if output_path.exists():
        raise FileExistsError(
            f"Evaluation results already exist: {output_path}. "
            "Rename or archive the existing file before running again."
        )

    dataset = load_dataset()
    dataset_hash = hashlib.sha256(DATASET_PATH.read_bytes()).hexdigest()
    correct = 0
    results = []

    for record in dataset:
        state: State = {
            "message": record["input"],
            "category": None,
            "answer": "",
            "classification_attempts": 0,
            "classification_error": None,
            "retry_instructions": None,
        }

        result = classify(state, prompt_version=prompt_version)

        predicted = result["category"]
        predicted_category = predicted.value if predicted is not None else None
        expected_category = record["expected_category"]

        is_correct = predicted_category == expected_category
        correct += int(is_correct)

        results.append(
            {
                "id": record["id"],
                "case_type": record["case_type"],
                "expected_category": expected_category,
                "predicted_category": predicted_category,
                "correct": is_correct,
            }
        )

        status = "PASS" if is_correct else "FAIL"

        print(
            f"[{record['id']}] {status} | "
            f"Expected: {expected_category} | "
            f"Predicted: {predicted_category}"
        )

    accuracy = correct / len(dataset)

    print("\n--- CLASSIFICATION EVALUATION ---")
    print(f"Total cases: {len(dataset)}")
    print(f"Correct: {correct}")
    print(f"Incorrect: {len(dataset) - correct}")
    print(f"Accuracy: {accuracy:.2%}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            {
                "experiment": experiment_name,
                "configuration": {
                    "model": MODEL_NAME,
                    "temperature": MODEL_TEMPERATURE,
                    "classification_prompt_version": prompt_version,
                    "dataset": "message_classification.jsonl",
                    "dataset_size": len(dataset),
                    "dataset_sha256": dataset_hash,
                },
                "total_cases": len(dataset),
                "correct": correct,
                "accuracy": accuracy,
                "results": results,
            },
            file,
            ensure_ascii=False,
            indent=2,
        )

    print(f"Results saved to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Evaluate a specific NovaShop classification prompt version."
    )

    parser.add_argument(
        "--prompt-version",
        type=int,
        required=True,
        help="Langfuse prompt version to evaluate.",
    )

    args = parser.parse_args()

    evaluate_classification(prompt_version=args.prompt_version)
