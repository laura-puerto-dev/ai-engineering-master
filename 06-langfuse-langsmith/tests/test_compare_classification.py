import json

import pytest

from evaluation.compare_classification import compare_classification


def write_experiments(tmp_path, baseline, candidate):
    baseline_path = tmp_path / "baseline.json"
    candidate_path = tmp_path / "candidate.json"

    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    candidate_path.write_text(json.dumps(candidate), encoding="utf-8")

    return baseline_path, candidate_path


def test_rejects_different_datasets(tmp_path):
    baseline = {
        "configuration": {
            "dataset_sha256": "hash-original",
        }
    }
    candidate = {
        "configuration": {
            "dataset_sha256": "hash-different",
        }
    }

    baseline_path, candidate_path = write_experiments(tmp_path, baseline, candidate)

    with pytest.raises(ValueError, match="datasets differ"):
        compare_classification(baseline_path, candidate_path)


def test_rejects_different_models(tmp_path):
    baseline = {
        "configuration": {
            "dataset_sha256": "same-hash",
            "model": "llama3.1",
        }
    }
    candidate = {
        "configuration": {
            "dataset_sha256": "same-hash",
            "model": "another-model",
        }
    }

    baseline_path, candidate_path = write_experiments(tmp_path, baseline, candidate)

    with pytest.raises(ValueError, match="'model' differs"):
        compare_classification(baseline_path, candidate_path)


def test_rejects_different_temperatures(tmp_path):
    baseline = {
        "configuration": {
            "dataset_sha256": "same-hash",
            "model": "llama3.1",
            "temperature": 0,
        }
    }
    candidate = {
        "configuration": {
            "dataset_sha256": "same-hash",
            "model": "llama3.1",
            "temperature": 0.7,
        }
    }

    baseline_path, candidate_path = write_experiments(tmp_path, baseline, candidate)

    with pytest.raises(ValueError, match="'temperature' differs"):
        compare_classification(baseline_path, candidate_path)


def test_rejects_duplicate_case_ids(tmp_path):
    baseline = {
        "configuration": {
            "dataset_sha256": "same-hash",
            "model": "llama3.1",
            "temperature": 0,
        },
        "results": [
            {"id": "001"},
            {"id": "001"},
        ],
    }

    candidate = {
        "configuration": {
            "dataset_sha256": "same-hash",
            "model": "llama3.1",
            "temperature": 0,
        },
        "results": [
            {"id": "001"},
            {"id": "002"},
        ],
    }

    baseline_path, candidate_path = write_experiments(tmp_path, baseline, candidate)

    with pytest.raises(ValueError, match="duplicate case IDs in baseline"):
        compare_classification(baseline_path, candidate_path)


def test_rejects_different_case_ids(tmp_path):
    baseline = {
        "configuration": {
            "dataset_sha256": "same-hash",
            "model": "llama3.1",
            "temperature": 0,
        },
        "results": [
            {"id": "001"},
            {"id": "002"},
        ],
    }

    candidate = {
        "configuration": {
            "dataset_sha256": "same-hash",
            "model": "llama3.1",
            "temperature": 0,
        },
        "results": [
            {"id": "001"},
            {"id": "003"},
        ],
    }

    baseline_path, candidate_path = write_experiments(tmp_path, baseline, candidate)

    with pytest.raises(ValueError, match="case IDs differ"):
        compare_classification(baseline_path, candidate_path)


def test_rejects_different_expected_categories(tmp_path):
    baseline = {
        "configuration": {
            "dataset_sha256": "same-hash",
            "model": "llama3.1",
            "temperature": 0,
        },
        "results": [
            {"id": "001", "expected_category": "pregunta"},
        ],
    }

    candidate = {
        "configuration": {
            "dataset_sha256": "same-hash",
            "model": "llama3.1",
            "temperature": 0,
        },
        "results": [
            {"id": "001", "expected_category": "queja"},
        ],
    }

    baseline_path, candidate_path = write_experiments(tmp_path, baseline, candidate)

    with pytest.raises(ValueError, match="expected category differs"):
        compare_classification(baseline_path, candidate_path)


def test_rejects_inconsistent_correct_value(tmp_path):
    baseline = {
        "configuration": {
            "dataset_sha256": "same-hash",
            "model": "llama3.1",
            "temperature": 0,
        },
        "results": [
            {
                "id": "001",
                "expected_category": "pregunta",
                "predicted_category": "queja",
                "correct": True,
            },
        ],
    }

    candidate = {
        "configuration": {
            "dataset_sha256": "same-hash",
            "model": "llama3.1",
            "temperature": 0,
        },
        "results": [
            {
                "id": "001",
                "expected_category": "pregunta",
                "predicted_category": "pregunta",
                "correct": True,
            },
        ],
    }

    baseline_path, candidate_path = write_experiments(tmp_path, baseline, candidate)

    with pytest.raises(ValueError, match="inconsistent 'correct' value"):
        compare_classification(baseline_path, candidate_path)


def test_rejects_inconsistent_aggregate_metrics(tmp_path):
    baseline = {
        "configuration": {
            "dataset_sha256": "same-hash",
            "model": "llama3.1",
            "temperature": 0,
        },
        "results": [
            {
                "id": "001",
                "expected_category": "pregunta",
                "predicted_category": "pregunta",
                "correct": True,
            },
        ],
        "total_cases": 1,
        "correct": 1,
        "accuracy": 0.5,
    }

    candidate = {
        **baseline,
        "accuracy": 1.0,
    }

    baseline_path, candidate_path = write_experiments(tmp_path, baseline, candidate)

    with pytest.raises(ValueError, match="inconsistent aggregate metrics"):
        compare_classification(baseline_path, candidate_path)


def test_compares_valid_experiments(tmp_path, capsys):
    baseline = {
        "experiment": "classification_v1",
        "configuration": {
            "dataset_sha256": "same-hash",
            "model": "llama3.1",
            "temperature": 0,
        },
        "results": [
            {
                "id": "001",
                "expected_category": "pregunta",
                "predicted_category": "queja",
                "correct": False,
            },
            {
                "id": "002",
                "expected_category": "queja",
                "predicted_category": "queja",
                "correct": True,
            },
        ],
        "total_cases": 2,
        "correct": 1,
        "accuracy": 0.5,
    }

    candidate = {
        **baseline,
        "experiment": "classification_v2",
        "results": [
            {
                "id": "001",
                "expected_category": "pregunta",
                "predicted_category": "pregunta",
                "correct": True,
            },
            {
                "id": "002",
                "expected_category": "queja",
                "predicted_category": "pregunta",
                "correct": False,
            },
        ],
    }

    baseline_path, candidate_path = write_experiments(tmp_path, baseline, candidate)

    compare_classification(baseline_path, candidate_path)

    output = capsys.readouterr().out

    assert "Baseline: classification_v1 (50.00%)" in output
    assert "Candidate: classification_v2 (50.00%)" in output
    assert "Accuracy difference: +0.00 percentage points" in output
    assert "Fixed cases: 1" in output
    assert "001: queja -> pregunta" in output
    assert "Regressions: 1" in output
    assert "002: queja -> pregunta" in output
