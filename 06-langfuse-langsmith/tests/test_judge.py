import pytest
from pydantic import ValidationError

from evaluation.judge import CriterionEvaluation, ResponseEvaluation


def test_criterion_accepts_valid_score():
    evaluation = CriterionEvaluation(
        score=4,
        reason="The response is relevant.",
    )

    assert evaluation.score == 4
    assert evaluation.reason == "The response is relevant."


@pytest.mark.parametrize("score", [0, 6])
def test_criterion_rejects_out_of_range_score(score):
    with pytest.raises(ValidationError):
        CriterionEvaluation(
            score=score,
            reason="Invalid score.",
        )


def test_response_evaluation_contains_three_criteria():
    evaluation = ResponseEvaluation(
        relevance=CriterionEvaluation(
            score=5,
            reason="Directly answers the question.",
        ),
        empathy=CriterionEvaluation(
            score=4,
            reason="Professional tone.",
        ),
        groundedness=CriterionEvaluation(
            score=5,
            reason="Supported by company context.",
        ),
    )

    assert evaluation.relevance.score == 5
    assert evaluation.empathy.score == 4
    assert evaluation.groundedness.score == 5
