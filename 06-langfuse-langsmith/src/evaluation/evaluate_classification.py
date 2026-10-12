import json
from pathlib import Path

from message_classifier.classifier import State, classify
from message_classifier.config import MODEL_NAME, MODEL_TEMPERATURE

DATASET_PATH = (
    Path(__file__).resolve().parents[2] / "datasets" / "message_classification.jsonl"
)


def load_dataset() -> list[dict]:
    with DATASET_PATH.open(encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def evaluate_classification() -> None:
    dataset = load_dataset()
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

        result = classify(state)

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

    output_path = (
        Path(__file__).resolve().parents[2]
        / "results"
        / "classification_baseline_v1.json"
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            {
                "experiment": "classification_baseline_v1",
                "configuration": {
                    "model": MODEL_NAME,
                    "temperature": MODEL_TEMPERATURE,
                    "classification_prompt_version": "v1",
                    "dataset": "message_classification.jsonl",
                    "dataset_size": len(dataset),
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
    evaluate_classification()
