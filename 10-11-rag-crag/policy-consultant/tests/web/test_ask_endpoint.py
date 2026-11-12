"""Tests for POST /api/ask.

Real PostgreSQL + RLS is used for the chunk retrieval/citation
behavior (reusing the seeded synthetic unit-vector pattern already
established in tests/test_rag.py and tests/test_retrieval.py), but the
embedding model and the answer generator are fakes, so no real BGE-M3
weights are loaded and no real Anthropic call is made.

A bare TestClient(app) — never entered as `with TestClient(app) as c:`
— is used deliberately throughout: entering it would run
web.app.lifespan, which loads the real BGE-M3 model and constructs a
real Anthropic client. Instead, app.state is populated directly with
fakes before each test, the same attributes the real lifespan would
otherwise set.

web.app.ask() opens app_connection() with no explicit dbname, so it
connects to whatever POSTGRES_DB points at — the real `use_test_database`
fixture below redirects that to the dedicated test database for the
duration of each PostgreSQL-backed test, the same one seeded_chunks and
policy_app_ready already write to.
"""

from __future__ import annotations

from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

from policy_consultant.corpus_manifest import load_access_model
from policy_consultant.models import AccessModel, Citation, GeneratedAnswer, RetrievedChunk
from web.app import app

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ACCESS_MODEL_PATH = PROJECT_ROOT / "config" / "access-model.yaml"
TEST_DATABASE_NAME = "policy_consultant_test"
DIMENSIONS = 1024

client = TestClient(app)


def _unit_vector(index: int) -> list[float]:
    vector = [0.0] * DIMENSIONS
    vector[index] = 1.0
    return vector


class _FakeEmbeddingModel:
    """embed_batch always returns the same pre-selected vector,
    regardless of the question text — each test controls which seeded
    chunk ends up closest by choosing that vector, not by what the
    question actually says.
    """

    def __init__(self, vector: list[float]) -> None:
        self._vector = vector

    @property
    def model_id(self) -> str:
        return "fake-model"

    @property
    def dimensions(self) -> int:
        return len(self._vector)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._vector for _ in texts]


class _FakeGenerator:
    def __init__(
        self, answer: GeneratedAnswer | None = None, error: Exception | None = None
    ) -> None:
        self._answer = answer
        self._error = error
        self.calls: list[tuple[str, list[RetrievedChunk]]] = []

    def generate_answer(self, question: str, chunks: list[RetrievedChunk]) -> GeneratedAnswer:
        self.calls.append((question, chunks))
        if self._error is not None:
            raise self._error
        assert self._answer is not None
        return self._answer


@pytest.fixture
def access_model() -> AccessModel:
    return load_access_model(ACCESS_MODEL_PATH)


def _set_app_state(access_model: AccessModel, embedding_model: object, generator: object) -> None:
    app.state.access_model = access_model
    app.state.embedding_model = embedding_model
    app.state.generator = generator


@pytest.fixture
def use_test_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTGRES_DB", TEST_DATABASE_NAME)


@pytest.fixture
def seeded_chunks(policy_app_ready: psycopg.Connection) -> psycopg.Connection:
    admin = policy_app_ready
    for document_id, country, allowed_roles, vector_index in [
        ("ES-001", "spain", ["employee", "manager", "hr"], 0),
        ("MX-001", "mexico", ["employee", "manager", "hr"], 1),
    ]:
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


# --- Input validation and profile selection: no PostgreSQL needed, ---
# --- these all fail before app_connection is ever opened.           ---


def test_ask_rejects_an_unknown_profile_id(access_model: AccessModel) -> None:
    _set_app_state(access_model, _FakeEmbeddingModel(_unit_vector(0)), _FakeGenerator())

    response = client.post("/api/ask", json={"profile_id": "does-not-exist", "question": "Q"})

    assert response.status_code == 400


def test_ask_rejects_a_missing_question(access_model: AccessModel) -> None:
    _set_app_state(access_model, _FakeEmbeddingModel(_unit_vector(0)), _FakeGenerator())

    response = client.post("/api/ask", json={"profile_id": "spain-employee"})

    assert response.status_code == 422


def test_ask_rejects_an_empty_question(access_model: AccessModel) -> None:
    _set_app_state(access_model, _FakeEmbeddingModel(_unit_vector(0)), _FakeGenerator())

    response = client.post("/api/ask", json={"profile_id": "spain-employee", "question": ""})

    assert response.status_code == 422


def test_ask_rejects_a_whitespace_only_question(access_model: AccessModel) -> None:
    """str_strip_whitespace strips before min_length is checked, so a
    question made entirely of spaces is rejected as empty.
    """
    _set_app_state(access_model, _FakeEmbeddingModel(_unit_vector(0)), _FakeGenerator())

    response = client.post("/api/ask", json={"profile_id": "spain-employee", "question": "   "})

    assert response.status_code == 422


def test_ask_rejects_extra_fields_like_country_or_role(access_model: AccessModel) -> None:
    """country/role must never be accepted as if they were part of the
    request's identity — only profile_id and question are valid.
    """
    _set_app_state(access_model, _FakeEmbeddingModel(_unit_vector(0)), _FakeGenerator())

    response = client.post(
        "/api/ask",
        json={"profile_id": "spain-employee", "question": "Q", "country": "spain"},
    )

    assert response.status_code == 422


# --- RLS, abstention, and error handling: real PostgreSQL. ---


@pytest.mark.integration
def test_ask_returns_a_grounded_answer_with_citation_text(
    use_test_database: None, seeded_chunks: psycopg.Connection, access_model: AccessModel
) -> None:
    fake_generator = _FakeGenerator(
        GeneratedAnswer(
            answer="Grounded answer",
            citations=[
                Citation(
                    document_id="ES-001",
                    version="1.0",
                    section_path=["1. Section"],
                    chunk_id="ES-001:1.0:0",
                )
            ],
            abstained=False,
        )
    )
    _set_app_state(access_model, _FakeEmbeddingModel(_unit_vector(0)), fake_generator)

    response = client.post(
        "/api/ask",
        json={"profile_id": "spain-employee", "question": "How many vacation days?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["abstained"] is False
    assert body["answer"] == "Grounded answer"
    assert body["citations"] == [
        {
            "document_id": "ES-001",
            "version": "1.0",
            "section_path": ["1. Section"],
            "chunk_id": "ES-001:1.0:0",
            "text": "Text of ES-001",
        }
    ]


@pytest.mark.integration
def test_ask_resolves_country_and_role_from_the_profile_not_the_request(
    use_test_database: None, seeded_chunks: psycopg.Connection, access_model: AccessModel
) -> None:
    """The closest possible vector match is MX-001's — unauthorized for
    the spain-employee profile. If this chunk ever reached the
    generator, it would mean app_connection was opened with the wrong
    (or no) country/role, since there is nothing else here that could
    have filtered it out.
    """
    fake_generator = _FakeGenerator(
        GeneratedAnswer(answer="unused", citations=[], abstained=False)
    )
    _set_app_state(access_model, _FakeEmbeddingModel(_unit_vector(1)), fake_generator)

    response = client.post(
        "/api/ask", json={"profile_id": "spain-employee", "question": "question"}
    )

    assert response.status_code == 200
    assert len(fake_generator.calls) == 1
    _, chunks = fake_generator.calls[0]
    assert all(chunk["document_id"] != "MX-001" for chunk in chunks)
    assert any(chunk["document_id"] == "ES-001" for chunk in chunks)


@pytest.mark.integration
def test_ask_returns_the_normal_abstention_when_there_is_no_evidence(
    use_test_database: None, policy_app_ready: psycopg.Connection, access_model: AccessModel
) -> None:
    fake_generator = _FakeGenerator(
        GeneratedAnswer(answer="unused", citations=[], abstained=False)
    )
    _set_app_state(access_model, _FakeEmbeddingModel(_unit_vector(0)), fake_generator)

    response = client.post("/api/ask", json={"profile_id": "spain-employee", "question": "q"})

    assert response.status_code == 200
    body = response.json()
    assert body["abstained"] is True
    assert body["citations"] == []
    # rag.answer_question never calls the generator when nothing is
    # indexed — this must stay a normal response, not an HTTP error.
    assert fake_generator.calls == []


@pytest.mark.integration
def test_ask_returns_a_generic_technical_error_without_leaking_details(
    use_test_database: None, seeded_chunks: psycopg.Connection, access_model: AccessModel
) -> None:
    fake_generator = _FakeGenerator(error=RuntimeError("some internal detail"))
    _set_app_state(access_model, _FakeEmbeddingModel(_unit_vector(0)), fake_generator)

    response = client.post("/api/ask", json={"profile_id": "spain-employee", "question": "q"})

    assert response.status_code == 502
    assert "some internal detail" not in response.text
