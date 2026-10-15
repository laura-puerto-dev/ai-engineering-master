import hashlib
import json
from pathlib import Path
from typing import cast

from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from evaluation.judge import ResponseEvaluation, evaluate_response
from message_classifier.classifier import Category, State, app
from message_classifier.config import (
    JUDGE_MODEL_NAME,
    JUDGE_MODEL_TEMPERATURE,
    MODEL_NAME,
    MODEL_TEMPERATURE,
)


class ResponseCase(BaseModel):
    id: str = Field(min_length=1)
    case_type: str = Field(min_length=1)
    message: str = Field(min_length=1)
    expected_category: str


class ResponseResult(BaseModel):
    id: str
    case_type: str
    message: str
    expected_category: str
    predicted_category: str | None
    classification_correct: bool
    answer: str
    evaluation: ResponseEvaluation | None


class ResponseExperiment(BaseModel):
    prompt_version: int
    model: str
    temperature: float
    judge_model: str
    judge_temperature: float
    dataset_sha256: str
    total_cases: int
    correct_classifications: int
    classification_accuracy: float
    results: list[ResponseResult]


def load_dataset(path: Path) -> list[ResponseCase]:
    cases = []
    seen_ids = set()

    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            data = json.loads(line)
            case = ResponseCase.model_validate(data)

            if case.expected_category not in {"pregunta", "queja"}:
                raise ValueError(
                    f"Invalid category on line {line_number}: {case.expected_category}"
                )

            if case.id in seen_ids:
                raise ValueError(f"Duplicate case ID: {case.id}")

            seen_ids.add(case.id)
            cases.append(case)

    if not cases:
        raise ValueError("The response evaluation dataset is empty.")

    return cases


def run_graph(
    case: ResponseCase,
    prompt_version: int,
) -> State:
    initial_state: State = {
        "message": case.message,
        "category": None,
        "answer": "",
        "classification_attempts": 0,
        "classification_error": None,
        "retry_instructions": None,
    }

    config: RunnableConfig = {
        "configurable": {
            "classification_prompt_version": prompt_version,
        }
    }

    result = app.invoke(initial_state, config=config)

    if not isinstance(result, dict):
        raise TypeError("Graph output must be a dictionary.")

    if not isinstance(result.get("category"), Category):
        raise TypeError("Graph output contains an invalid category.")

    if not isinstance(result.get("answer"), str):
        raise TypeError("Graph output contains an invalid answer.")

    return cast(State, result)


def evaluate_case(
    case: ResponseCase,
    prompt_version: int,
) -> ResponseResult:
    result = run_graph(case, prompt_version)

    category = result["category"]
    answer = result["answer"]

    predicted_category = category.value if isinstance(category, Category) else None

    evaluation = None

    if predicted_category is not None and answer.strip():
        evaluation = evaluate_response(
            message=case.message,
            category=predicted_category,
            answer=answer,
        )

    return ResponseResult(
        id=case.id,
        case_type=case.case_type,
        message=case.message,
        expected_category=case.expected_category,
        predicted_category=predicted_category,
        classification_correct=predicted_category == case.expected_category,
        answer=answer,
        evaluation=evaluation,
    )


def evaluate_dataset(
    cases: list[ResponseCase],
    prompt_version: int,
) -> list[ResponseResult]:
    results = []

    for case in cases:
        print(f"Evaluating case {case.id}: {case.case_type}")

        result = evaluate_case(
            case=case,
            prompt_version=prompt_version,
        )

        results.append(result)

    return results


def build_experiment(
    results: list[ResponseResult],
    prompt_version: int,
    dataset_path: Path,
) -> ResponseExperiment:
    if not results:
        raise ValueError("Cannot build an experiment without results.")

    total_cases = len(results)
    correct_classifications = sum(result.classification_correct for result in results)

    dataset_sha256 = hashlib.sha256(dataset_path.read_bytes()).hexdigest()

    return ResponseExperiment(
        prompt_version=prompt_version,
        model=MODEL_NAME,
        temperature=MODEL_TEMPERATURE,
        judge_model=JUDGE_MODEL_NAME,
        judge_temperature=JUDGE_MODEL_TEMPERATURE,
        dataset_sha256=dataset_sha256,
        total_cases=total_cases,
        correct_classifications=correct_classifications,
        classification_accuracy=correct_classifications / total_cases,
        results=results,
    )


def save_experiment(
    experiment: ResponseExperiment,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        experiment.model_dump_json(indent=2),
        encoding="utf-8",
    )
