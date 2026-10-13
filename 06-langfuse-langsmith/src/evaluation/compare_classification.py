import argparse
import json
from pathlib import Path


def load_experiment(path: Path) -> dict:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def compare_classification(baseline_path: Path, candidate_path: Path) -> None:
    baseline = load_experiment(baseline_path)
    candidate = load_experiment(candidate_path)

    baseline_hash = baseline["configuration"]["dataset_sha256"]
    candidate_hash = candidate["configuration"]["dataset_sha256"]

    if baseline_hash != candidate_hash:
        raise ValueError(
            "Cannot compare experiments: datasets differ. "
            "Both experiments must use the same dataset."
        )

    for parameter in ("model", "temperature"):
        baseline_value = baseline["configuration"][parameter]
        candidate_value = candidate["configuration"][parameter]

        if baseline_value != candidate_value:
            raise ValueError(
                f"Cannot compare experiments: '{parameter}' differs. "
                f"Baseline: {baseline_value!r}, "
                f"Candidate: {candidate_value!r}."
            )

    baseline_cases = {record["id"]: record for record in baseline["results"]}
    candidate_cases = {record["id"]: record for record in candidate["results"]}

    if len(baseline_cases) != len(baseline["results"]):
        raise ValueError("Cannot compare experiments: duplicate case IDs in baseline.")

    if len(candidate_cases) != len(candidate["results"]):
        raise ValueError("Cannot compare experiments: duplicate case IDs in candidate.")

    if baseline_cases.keys() != candidate_cases.keys():
        raise ValueError("Cannot compare experiments: case IDs differ.")

    for case_id in baseline_cases:
        baseline_expected = baseline_cases[case_id]["expected_category"]
        candidate_expected = candidate_cases[case_id]["expected_category"]

        if baseline_expected != candidate_expected:
            raise ValueError(
                f"Cannot compare experiments: expected category differs "
                f"for case {case_id}."
            )

    for experiment_name, cases in (
        ("baseline", baseline_cases),
        ("candidate", candidate_cases),
    ):
        for case_id, record in cases.items():
            actual_correct = record["predicted_category"] == record["expected_category"]

            if record["correct"] != actual_correct:
                raise ValueError(
                    f"Cannot compare experiments: inconsistent 'correct' "
                    f"value in {experiment_name}, case {case_id}."
                )

    for experiment_name, experiment in (
        ("baseline", baseline),
        ("candidate", candidate),
    ):
        results = experiment["results"]

        actual_total = len(results)
        actual_correct = sum(record["correct"] for record in results)
        actual_accuracy = actual_correct / actual_total if actual_total else 0.0

        if (
            experiment["total_cases"] != actual_total
            or experiment["correct"] != actual_correct
            or abs(experiment["accuracy"] - actual_accuracy) > 1e-9
        ):
            raise ValueError(
                f"Cannot compare experiments: inconsistent aggregate metrics "
                f"in {experiment_name}."
            )

    baseline_accuracy = baseline["accuracy"]
    candidate_accuracy = candidate["accuracy"]

    accuracy_delta = (candidate_accuracy - baseline_accuracy) * 100

    fixed_cases = []
    regressions = []

    for case_id, baseline_case in baseline_cases.items():
        candidate_case = candidate_cases[case_id]

        if not baseline_case["correct"] and candidate_case["correct"]:
            fixed_cases.append(case_id)

        elif baseline_case["correct"] and not candidate_case["correct"]:
            regressions.append(case_id)

    print("\n--- CLASSIFICATION COMPARISON ---")
    print(f"Baseline: {baseline['experiment']} ({baseline_accuracy:.2%})")
    print(f"Candidate: {candidate['experiment']} ({candidate_accuracy:.2%})")
    print(f"Accuracy difference: {accuracy_delta:+.2f} percentage points")

    print(f"\nFixed cases: {len(fixed_cases)}")

    for case_id in fixed_cases:
        previous = baseline_cases[case_id]["predicted_category"]
        current = candidate_cases[case_id]["predicted_category"]
        print(f"  {case_id}: {previous} -> {current}")

    print(f"\nRegressions: {len(regressions)}")

    for case_id in regressions:
        previous = baseline_cases[case_id]["predicted_category"]
        current = candidate_cases[case_id]["predicted_category"]
        print(f"  {case_id}: {previous} -> {current}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compare two classification evaluation experiments."
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        required=True,
        help="Path to the baseline experiment JSON.",
    )
    parser.add_argument(
        "--candidate",
        type=Path,
        required=True,
        help="Path to the candidate experiment JSON.",
    )

    args = parser.parse_args()

    compare_classification(
        baseline_path=args.baseline,
        candidate_path=args.candidate,
    )
