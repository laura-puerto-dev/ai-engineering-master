from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

from evaluation.judge_prompts import JUDGE_PROMPT
from message_classifier.config import (
    COMPANY_CONTEXT,
    MODEL_NAME,
    MODEL_TEMPERATURE,
)


class CriterionEvaluation(BaseModel):
    score: int = Field(
        ge=1,
        le=5,
        description="Score from 1 (very poor) to 5 (excellent).",
    )
    reason: str = Field(
        description="Brief justification for the assigned score.",
    )


class ResponseEvaluation(BaseModel):
    relevance: CriterionEvaluation
    empathy: CriterionEvaluation
    groundedness: CriterionEvaluation


def evaluate_response(
    message: str,
    category: str,
    answer: str,
) -> ResponseEvaluation:
    llm = ChatOllama(
        model=MODEL_NAME,
        temperature=MODEL_TEMPERATURE,
    )

    structured_llm = llm.with_structured_output(ResponseEvaluation)

    chain = JUDGE_PROMPT | structured_llm

    result = chain.invoke(
        {
            "company_context": COMPANY_CONTEXT,
            "category": category,
            "message": message,
            "answer": answer,
        }
    )

    if not isinstance(result, ResponseEvaluation):
        raise TypeError(f"Unexpected judge output type: {type(result).__name__}")

    return result
