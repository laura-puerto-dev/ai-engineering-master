"""Tests for POST /api/ask's mode="crag" path (Fase 5A: CRAG wired into
the demo web app, alongside the existing "rag" default).

Same real-PostgreSQL-plus-fakes convention as test_ask_endpoint.py:
retrieval/RLS runs for real, but the reranker, evidence grader, query
reformulator, embedding model, and answer generator are all fakes —
no real model weights are loaded, no real Anthropic call is made. This
file never exercises crag.answer_question_crag's own internal logic
(that's test_crag.py's job) — it only checks that web/app.py wires a
request into that real graph correctly: profile→RLS, mode dispatch,
model reuse, trace shape, and error handling.

A bare TestClient(app) is used throughout, for the same reason
test_ask_endpoint.py gives: entering it as a context manager would run
the real lifespan and load real models.
"""

from __future__ import annotations

from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

import web.app as web_app
from policy_consultant.corpus_manifest import load_access_model
from policy_consultant.models import (
    AccessModel,
    Citation,
    EvidenceGrade,
    GeneratedAnswer,
    RerankedChunk,
    RetrievedChunk,
)
from web.app import CragComponents, app

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
    """Same convention as test_ask_endpoint.py's own fake: always
    returns the same pre-selected vector, regardless of the text it was
    asked to embed — including a CRAG reformulated query's text, which
    this fake deliberately does not distinguish from the original
    question.
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


class _FakeReranker:
    """Preserves order and attaches a fixed rerank_score — these tests
    only care about which chunk_ids reach the grader, never about
    score-based reordering (reranking.py's own tests already cover
    that), so a real ranking decision would be wasted complexity here.
    """

    def rerank(self, query: str, chunks: list[RetrievedChunk]) -> list[RerankedChunk]:
        return [
            RerankedChunk(
                chunk_id=chunk["chunk_id"],
                document_id=chunk["document_id"],
                version=chunk["version"],
                section_path=chunk["section_path"],
                text=chunk["text"],
                distance=chunk["distance"],
                rerank_score=1.0,
            )
            for chunk in chunks
        ]


class _FakeGrader:
    """Returns one scripted EvidenceGrade per call, in order — lets a
    test drive the real CRAG graph through a specific route sequence
    (e.g. ambiguous then sufficient) without any real Claude call.
    """

    def __init__(self, grades: list[EvidenceGrade]) -> None:
        self._grades = list(grades)
        self.calls: list[tuple[str, list[RerankedChunk]]] = []

    def grade(self, question: str, chunks: list[RerankedChunk]) -> EvidenceGrade:
        self.calls.append((question, chunks))
        return self._grades[len(self.calls) - 1]


class _FakeReformulator:
    def __init__(self, queries: list[str]) -> None:
        self._queries = list(queries)
        self.calls = 0

    def reformulate(self, *, question: str, previous_query: str, missing_aspects: list[str]) -> str:
        query = self._queries[self.calls]
        self.calls += 1
        return query


@pytest.fixture
def access_model() -> AccessModel:
    return load_access_model(ACCESS_MODEL_PATH)


def _set_app_state(
    access_model: AccessModel,
    embedding_model: object,
    generator: object,
    crag_components: CragComponents | None = None,
) -> None:
    app.state.access_model = access_model
    app.state.embedding_model = embedding_model
    app.state.generator = generator
    if crag_components is not None:
        app.state.crag_components = crag_components
    elif hasattr(app.state, "crag_components"):
        del app.state.crag_components


@pytest.fixture
def use_test_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTGRES_DB", TEST_DATABASE_NAME)


@pytest.fixture
def seeded_chunks(policy_app_ready: psycopg.Connection) -> psycopg.Connection:
    """Same two documents/chunks as test_ask_endpoint.py's own fixture:
    one authorized for spain-employee (ES-001), one that must never
    reach the generator under that profile (MX-001) — reused here to
    confirm RLS holds for CRAG's internal retrievals too, including the
    one that follows a reformulation.
    """
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


# --- Input validation: no PostgreSQL needed, fails before app_connection. ---


def test_ask_rejects_an_invalid_mode(access_model: AccessModel) -> None:
    _set_app_state(access_model, _FakeEmbeddingModel(_unit_vector(0)), _FakeGenerator())

    response = client.post(
        "/api/ask",
        json={"profile_id": "spain-employee", "question": "Q", "mode": "not-a-real-mode"},
    )

    assert response.status_code == 422


# --- Backward compatibility: a request that never sends `mode`. ---


@pytest.mark.integration
def test_ask_without_a_mode_field_defaults_to_rag_unchanged(
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
        "/api/ask", json={"profile_id": "spain-employee", "question": "How many vacation days?"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "rag"
    assert body["crag_trace"] is None
    assert body["abstained"] is False
    assert body["answer"] == "Grounded answer"


# --- Lazy loading: mode="rag" must never construct any CRAG component. ---


@pytest.mark.integration
def test_rag_mode_never_constructs_crag_components(
    use_test_database: None,
    seeded_chunks: psycopg.Connection,
    access_model: AccessModel,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("must not be constructed for a mode='rag' request")

    monkeypatch.setattr(web_app, "LocalQwen3RerankerModel", _boom)
    monkeypatch.setattr(web_app, "ClaudeEvidenceGrader", _boom)
    monkeypatch.setattr(web_app, "ClaudeQueryReformulator", _boom)

    fake_generator = _FakeGenerator(GeneratedAnswer(answer="unused", citations=[], abstained=False))
    _set_app_state(access_model, _FakeEmbeddingModel(_unit_vector(0)), fake_generator)

    response = client.post(
        "/api/ask", json={"profile_id": "spain-employee", "question": "q", "mode": "rag"}
    )

    assert response.status_code == 200


# --- mode="crag": RLS, successful correction, abstention, errors. -----------


@pytest.mark.integration
def test_crag_mode_resolves_country_and_role_from_the_profile_not_the_request(
    use_test_database: None, seeded_chunks: psycopg.Connection, access_model: AccessModel
) -> None:
    """Mirrors test_ask_endpoint.py's identical RAG test: MX-001 is the
    closest vector match but unauthorized for spain-employee. If it
    ever reached the grader (on any attempt, including after a
    reformulation), app_connection would have been opened with the
    wrong — or no — country/role.
    """
    grader = _FakeGrader(
        [
            EvidenceGrade(
                route="sufficient",
                covered_aspects=["x"],
                missing_aspects=[],
                useful_chunk_ids=["ES-001:1.0:0"],
                rationale="r",
            )
        ]
    )
    fake_generator = _FakeGenerator(GeneratedAnswer(answer="unused", citations=[], abstained=False))
    _set_app_state(
        access_model,
        _FakeEmbeddingModel(_unit_vector(1)),
        fake_generator,
        crag_components=CragComponents(
            reranker=_FakeReranker(), grader=grader, reformulator=_FakeReformulator([])
        ),
    )

    response = client.post(
        "/api/ask", json={"profile_id": "spain-employee", "question": "question", "mode": "crag"}
    )

    assert response.status_code == 200
    assert len(grader.calls) == 1
    _, chunks = grader.calls[0]
    assert all(chunk["document_id"] != "MX-001" for chunk in chunks)
    assert any(chunk["document_id"] == "ES-001" for chunk in chunks)


@pytest.mark.integration
def test_crag_mode_successful_correction_returns_trace_and_citations(
    use_test_database: None, seeded_chunks: psycopg.Connection, access_model: AccessModel
) -> None:
    """The scenario the Fase 5A brief asks for explicitly: a first
    ambiguous/insufficient grade, a reformulation, a second retrieval,
    a sufficient grade, and a generated answer with real citations and
    a trace that reflects exactly what happened.
    """
    grader = _FakeGrader(
        [
            EvidenceGrade(
                route="ambiguous",
                covered_aspects=["partial"],
                missing_aspects=["the rest"],
                useful_chunk_ids=["ES-001:1.0:0"],
                rationale="only partially covers it",
            ),
            EvidenceGrade(
                route="sufficient",
                covered_aspects=["partial", "the rest"],
                missing_aspects=[],
                useful_chunk_ids=["ES-001:1.0:0"],
                rationale="now it covers it",
            ),
        ]
    )
    reformulator = _FakeReformulator(["reformulated query text"])
    fake_generator = _FakeGenerator(
        GeneratedAnswer(
            answer="Grounded via CRAG",
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
    _set_app_state(
        access_model,
        _FakeEmbeddingModel(_unit_vector(0)),
        fake_generator,
        crag_components=CragComponents(
            reranker=_FakeReranker(), grader=grader, reformulator=reformulator
        ),
    )

    response = client.post(
        "/api/ask",
        json={"profile_id": "spain-employee", "question": "original question", "mode": "crag"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "crag"
    assert body["abstained"] is False
    assert body["answer"] == "Grounded via CRAG"
    assert body["citations"] == [
        {
            "document_id": "ES-001",
            "version": "1.0",
            "section_path": ["1. Section"],
            "chunk_id": "ES-001:1.0:0",
            "text": "Text of ES-001",
        }
    ]

    trace = body["crag_trace"]
    assert trace["retrieval_count"] == 2
    assert [attempt["route"] for attempt in trace["attempts"]] == ["ambiguous", "sufficient"]
    assert trace["attempts"][0]["query"] == "original question"
    assert trace["attempts"][1]["query"] == "reformulated query text"

    # Only the final, sufficient attempt's evidence reaches the generator.
    assert len(fake_generator.calls) == 1
    _, evidence = fake_generator.calls[0]
    assert [chunk["chunk_id"] for chunk in evidence] == ["ES-001:1.0:0"]

    # RLS must hold for every retrieval the grader ever sees, including
    # the one that follows the reformulation — MX-001 (mexico) is never
    # authorized for spain-employee, on either attempt.
    assert len(grader.calls) == 2
    for _, chunks_seen_by_grader in grader.calls:
        assert all(chunk["document_id"] != "MX-001" for chunk in chunks_seen_by_grader)
        assert any(chunk["document_id"] == "ES-001" for chunk in chunks_seen_by_grader)


@pytest.mark.integration
def test_crag_mode_abstains_after_exhausting_retrievals(
    use_test_database: None, seeded_chunks: psycopg.Connection, access_model: AccessModel
) -> None:
    grader = _FakeGrader(
        [
            EvidenceGrade(
                route="insufficient",
                covered_aspects=[],
                missing_aspects=["x"],
                useful_chunk_ids=[],
                rationale="r",
            )
        ]
        * 3
    )
    reformulator = _FakeReformulator(["q2", "q3"])
    fake_generator = _FakeGenerator(GeneratedAnswer(answer="unused", citations=[], abstained=False))
    _set_app_state(
        access_model,
        _FakeEmbeddingModel(_unit_vector(0)),
        fake_generator,
        crag_components=CragComponents(
            reranker=_FakeReranker(), grader=grader, reformulator=reformulator
        ),
    )

    response = client.post(
        "/api/ask", json={"profile_id": "spain-employee", "question": "q", "mode": "crag"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["abstained"] is True
    assert body["citations"] == []
    assert body["crag_trace"]["retrieval_count"] == 3
    # abstain_node never calls the generator over discarded/insufficient
    # evidence — this must stay true through the web layer too.
    assert fake_generator.calls == []


@pytest.mark.integration
def test_crag_mode_returns_a_generic_technical_error_without_leaking_details(
    use_test_database: None, seeded_chunks: psycopg.Connection, access_model: AccessModel
) -> None:
    class _BoomGrader:
        def grade(self, question: str, chunks: list[RerankedChunk]) -> EvidenceGrade:
            raise RuntimeError("some internal detail")

    fake_generator = _FakeGenerator(GeneratedAnswer(answer="unused", citations=[], abstained=False))
    _set_app_state(
        access_model,
        _FakeEmbeddingModel(_unit_vector(0)),
        fake_generator,
        crag_components=CragComponents(
            reranker=_FakeReranker(), grader=_BoomGrader(), reformulator=_FakeReformulator([])
        ),
    )

    response = client.post(
        "/api/ask", json={"profile_id": "spain-employee", "question": "q", "mode": "crag"}
    )

    assert response.status_code == 502
    assert "some internal detail" not in response.text


# --- _get_crag_components: pure, no DB, no TestClient. ----------------------


class _State:
    """A bare namespace, standing in for app.state (FastAPI's own State
    object) — _get_crag_components only ever calls getattr/setattr on
    whatever it's given, so this is enough.
    """


def test_get_crag_components_builds_once_and_reuses_the_same_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    build_count = {"reranker": 0, "grader": 0, "reformulator": 0}

    class _CountingReranker:
        def __init__(self, *, device: str) -> None:
            build_count["reranker"] += 1

    class _CountingGrader:
        def __init__(self) -> None:
            build_count["grader"] += 1

    class _CountingReformulator:
        def __init__(self) -> None:
            build_count["reformulator"] += 1

    monkeypatch.setattr(web_app, "LocalQwen3RerankerModel", _CountingReranker)
    monkeypatch.setattr(web_app, "ClaudeEvidenceGrader", _CountingGrader)
    monkeypatch.setattr(web_app, "ClaudeQueryReformulator", _CountingReformulator)

    state = _State()
    first = web_app._get_crag_components(state)
    second = web_app._get_crag_components(state)

    assert first is second
    assert build_count == {"reranker": 1, "grader": 1, "reformulator": 1}


def test_get_crag_components_does_not_cache_a_partial_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _BoomGrader:
        def __init__(self) -> None:
            raise RuntimeError("boom")

    monkeypatch.setattr(web_app, "LocalQwen3RerankerModel", lambda *, device: object())
    monkeypatch.setattr(web_app, "ClaudeEvidenceGrader", _BoomGrader)
    monkeypatch.setattr(web_app, "ClaudeQueryReformulator", lambda: object())

    state = _State()
    with pytest.raises(RuntimeError):
        web_app._get_crag_components(state)

    assert getattr(state, "crag_components", None) is None
