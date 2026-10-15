from pathlib import Path

from evaluation.evaluate_responses import load_dataset

DATASET_PATH = (
    Path(__file__).resolve().parents[1] / "datasets" / "response_evaluation.jsonl"
)


def test_load_response_dataset():
    cases = load_dataset(DATASET_PATH)

    assert len(cases) == 10
    assert len({case.id for case in cases}) == 10
    assert all(case.expected_category in {"pregunta", "queja"} for case in cases)
