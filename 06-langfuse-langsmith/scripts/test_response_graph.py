from pathlib import Path

from dotenv import load_dotenv

from evaluation.evaluate_responses import load_dataset, run_graph
from evaluation.judge import evaluate_response

DATASET_PATH = (
    Path(__file__).resolve().parents[1] / "datasets" / "response_evaluation.jsonl"
)


def main() -> None:
    load_dotenv(".env")

    cases = load_dataset(DATASET_PATH)
    case = cases[0]

    result = run_graph(case, prompt_version=2)

    print(f"Case: {case.id}")
    print(f"Message: {case.message}")
    print(f"Expected category: {case.expected_category}")
    print(f"Predicted category: {result['category']}")
    print(f"Answer: {result['answer']}")

    category = result["category"]

    if category is None:
        raise ValueError("Graph did not produce a classification.")

    evaluation = evaluate_response(
        message=case.message,
        category=category.value,
        answer=result["answer"],
    )

    print("\nLLM-as-Judge evaluation:")
    print(evaluation.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
