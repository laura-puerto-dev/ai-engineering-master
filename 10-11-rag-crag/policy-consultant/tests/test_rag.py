"""Integration tests for rag.py (src/policy_consultant/rag.py).

Uses a fake AnswerGenerator (never anthropic, never a real retrieval
helper beyond retrieve_relevant_chunks itself) to prove answer_question's
own wiring: it never calls the generator when there is no evidence, and
it never hands the generator a chunk that RLS would not have authorized.

The synthetic "unit vector" seeding pattern is duplicated from
test_retrieval.py rather than imported, per this project's established
convention of not cross-importing between test files.
"""

from __future__ import annotations

from pathlib import Path

import psycopg
import pytest

from policy_consultant.corpus_manifest import load_access_model
from policy_consultant.db import app_connection
from policy_consultant.models import AccessModel, GeneratedAnswer, RetrievedChunk
from policy_consultant.rag import answer_question

pytestmark = pytest.mark.integration

TEST_DATABASE_NAME = "policy_consultant_test"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ACCESS_MODEL_PATH = PROJECT_ROOT / "config" / "access-model.yaml"
DIMENSIONS = 1024

_DOCUMENTS = [
    # (document_id, country, allowed_roles, unit_vector_index)
    ("ES-001", "spain", ["employee", "manager", "hr"], 0),
    ("MX-001", "mexico", ["employee", "manager", "hr"], 1),
]


def _unit_vector(index: int) -> list[float]:
    vector = [0.0] * DIMENSIONS
    vector[index] = 1.0
    return vector


@pytest.fixture
def access_model() -> AccessModel:
    return load_access_model(ACCESS_MODEL_PATH)


@pytest.fixture
def seeded_chunks(policy_app_ready: psycopg.Connection) -> psycopg.Connection:
    admin = policy_app_ready
    for document_id, country, allowed_roles, vector_index in _DOCUMENTS:
        admin.execute(
            """
            INSERT INTO documents
                (document_id, version, country, language, allowed_roles, effective_from, path)
            VALUES (%s, '1.0', %s, 'es', %s, '2026-01-01', %s)
            """,
            (document_id, country, allowed_roles, f"data/corpus/{document_id}.md"),
        )
        admin.execute(
            """
            INSERT INTO chunks
                (chunk_id, document_id, ordinal, section_path, text, embedding, model_id)
            VALUES (%s, %s, 0, ARRAY['1. Section'], %s, %s, 'fake-model')
            """,
            (
                f"{document_id}:1.0:0",
                document_id,
                f"Text of {document_id}",
                _unit_vector(vector_index),
            ),
        )
    return admin


class _FakeGenerator:
    def __init__(self, answer: GeneratedAnswer) -> None:
        self._answer = answer
        self.calls: list[tuple[str, list[RetrievedChunk]]] = []

    def generate_answer(self, question: str, chunks: list[RetrievedChunk]) -> GeneratedAnswer:
        self.calls.append((question, chunks))
        return self._answer


def test_answer_question_does_not_call_the_generator_when_nothing_is_indexed(
    policy_app_ready: psycopg.Connection, access_model: AccessModel
) -> None:
    fake = _FakeGenerator(GeneratedAnswer(answer="unused", citations=[], abstained=False))

    with app_connection(
        country="spain", role="employee", access_model=access_model, dbname=TEST_DATABASE_NAME
    ) as conn:
        result = answer_question(
            conn, "question", query_embedding=_unit_vector(0), generator=fake, top_k=5
        )

    assert fake.calls == []
    assert result["abstained"] is True
    assert result["citations"] == []


@pytest.mark.parametrize(
    ("question", "expected_message"),
    [
        (
            "¿Cuántos días de vacaciones tengo?",
            "No se encontró evidencia suficiente para responder con garantías.",
        ),
        (
            "How many vacation days do I have?",
            "Not enough evidence was found to answer with confidence.",
        ),
    ],
)
def test_answer_question_localizes_the_no_evidence_fallback(
    policy_app_ready: psycopg.Connection,
    access_model: AccessModel,
    question: str,
    expected_message: str,
) -> None:
    fake = _FakeGenerator(GeneratedAnswer(answer="unused", citations=[], abstained=False))

    with app_connection(
        country="spain", role="employee", access_model=access_model, dbname=TEST_DATABASE_NAME
    ) as conn:
        result = answer_question(
            conn, question, query_embedding=_unit_vector(0), generator=fake, top_k=5
        )

    assert fake.calls == []
    assert result["answer"] == expected_message


def test_answer_question_delegates_to_the_generator_with_authorized_chunks(
    seeded_chunks: psycopg.Connection, access_model: AccessModel
) -> None:
    expected = GeneratedAnswer(answer="Grounded answer", citations=[], abstained=False)
    fake = _FakeGenerator(expected)

    with app_connection(
        country="spain", role="employee", access_model=access_model, dbname=TEST_DATABASE_NAME
    ) as conn:
        result = answer_question(
            conn,
            "How many vacation days?",
            query_embedding=_unit_vector(0),
            generator=fake,
            top_k=5,
        )

    assert len(fake.calls) == 1
    question, chunks = fake.calls[0]
    assert question == "How many vacation days?"
    assert {chunk["document_id"] for chunk in chunks} == {"ES-001"}
    assert result == expected


def test_answer_question_never_exposes_an_unauthorized_chunk_to_the_generator(
    seeded_chunks: psycopg.Connection, access_model: AccessModel
) -> None:
    fake = _FakeGenerator(GeneratedAnswer(answer="unused", citations=[], abstained=False))

    with app_connection(
        country="spain", role="employee", access_model=access_model, dbname=TEST_DATABASE_NAME
    ) as conn:
        # Query is the exact vector of MX-001's chunk (mexico, unauthorized
        # for a spain user) — the best possible mathematical match.
        answer_question(
            conn, "question", query_embedding=_unit_vector(1), generator=fake, top_k=5
        )

    assert len(fake.calls) == 1
    _, chunks = fake.calls[0]
    assert all(chunk["document_id"] != "MX-001" for chunk in chunks)
