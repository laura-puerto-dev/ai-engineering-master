import argparse
from pathlib import Path

from dotenv import load_dotenv

from evaluation.evaluate_responses import (
    build_experiment,
    evaluate_dataset,
    load_dataset,
    save_experiment,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = PROJECT_ROOT / "datasets" / "response_evaluation.jsonl"
RESULTS_DIR = PROJECT_ROOT / "results"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate LangGraph responses using LLM-as-Judge."
    )
    parser.add_argument(
        "--prompt-version",
        type=int,
        required=True,
        help="Langfuse classification prompt version to evaluate.",
    )
    args = parser.parse_args()

    if args.prompt_version < 1:
        parser.error("--prompt-version must be a positive integer.")

    load_dotenv(PROJECT_ROOT / ".env")

    cases = load_dataset(DATASET_PATH)

    results = evaluate_dataset(
        cases=cases,
        prompt_version=args.prompt_version,
    )

    experiment = build_experiment(
        results=results,
        prompt_version=args.prompt_version,
        dataset_path=DATASET_PATH,
    )

    output_path = RESULTS_DIR / f"responses_v{args.prompt_version}.json"
    save_experiment(experiment, output_path)

    print("\nEvaluation completed.")
    print(f"Total cases: {experiment.total_cases}")
    print(f"Classification accuracy: {experiment.classification_accuracy:.1%}")
    print(f"Results saved to: {output_path}")


if __name__ == "__main__":
    main()
