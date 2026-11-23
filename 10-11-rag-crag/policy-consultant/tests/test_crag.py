"""Tests for crag.py — the LangGraph CRAG graph.

Every dependency (retrieval, reranking, grading, reformulation,
generation) is a deterministic fake; no real PostgreSQL connection,
model weights, or Anthropic calls are involved anywhere in this file.
_build_graph is exercised directly (never answer_question_crag, which
only adds a real embedding+retrieval closure around it) with a real,
compiled LangGraph graph — the routing/limit logic itself is genuinely
executed, not mocked.
"""

from __future__ import annotations

from policy_consultant.crag import (
    MAX_RETRIEVALS,
    CragState,
    _build_graph,
    _initial_state,
    _merge_without_duplicates,
    _to_crag_result,
    _to_retrieved_chunk,
)
from policy_consultant.models import (
    EvidenceGrade,
    GeneratedAnswer,
    RerankedChunk,
    RetrievedChunk,
)
from policy_consultant.reranking import _build_ranked_chunks


def _make_retrieved_chunk(*, chunk_id: str, distance: float) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id=chunk_id.split(":")[0],
        version="1.0",
        section_path=["1. Section"],
        text=f"Text of {chunk_id}",
        distance=distance,
    )


def _make_reranked_chunk(*, chunk_id: str, distance: float, rerank_score: float) -> RerankedChunk:
    return RerankedChunk(
        chunk_id=chunk_id,
        document_id=chunk_id.split(":")[0],
        version="1.0",
        section_path=["1. Section"],
        text=f"Text of {chunk_id}",
        distance=distance,
        rerank_score=rerank_score,
    )


class _FakeRetriever:
    """Returns the next scripted page of candidates on each call, []
    once pages are exhausted. Records every query it was asked for.
    """

    def __init__(self, pages: list[list[RetrievedChunk]]) -> None:
        self._pages = pages
        self.queries: list[str] = []

    def __call__(self, query: str) -> list[RetrievedChunk]:
        self.queries.append(query)
        index = len(self.queries) - 1
        return self._pages[index] if index < len(self._pages) else []


class _FakeReranker:
    """Scores default to 1 - distance unless overridden by `scores`, and
    reuses the real reranking._build_ranked_chunks to sort/shape the
    result exactly like the production reranker would.
    """

    def __init__(self, scores: dict[str, float] | None = None) -> None:
        self._scores = scores or {}
        self.calls: list[tuple[str, list[RetrievedChunk]]] = []

    def rerank(self, query: str, chunks: list[RetrievedChunk]) -> list[RerankedChunk]:
        self.calls.append((query, chunks))
        if not chunks:
            return []
        scores = [self._scores.get(chunk["chunk_id"], 1 - chunk["distance"]) for chunk in chunks]
        return _build_ranked_chunks(chunks, scores)


class _FakeGrader:
    """Returns the next scripted EvidenceGrade on each call. Records the
    exact (question, chunks) pool it was given each time.
    """

    def __init__(self, grades: list[EvidenceGrade]) -> None:
        self._grades = grades
        self.calls: list[tuple[str, list[RerankedChunk]]] = []

    def grade(self, question: str, chunks: list[RerankedChunk]) -> EvidenceGrade:
        self.calls.append((question, chunks))
        return self._grades[len(self.calls) - 1]


class _FakeReformulator:
    """Returns the next scripted query on each call. Records the exact
    keyword arguments it was given each time.
    """

    def __init__(self, queries: list[str]) -> None:
        self._queries = queries
        self.calls: list[dict[str, object]] = []

    def reformulate(
        self, *, question: str, previous_query: str, missing_aspects: list[str]
    ) -> str:
        self.calls.append(
            {
                "question": question,
                "previous_query": previous_query,
                "missing_aspects": missing_aspects,
            }
        )
        return self._queries[len(self.calls) - 1]


class _FakeGenerator:
    def __init__(self, answer: GeneratedAnswer) -> None:
        self._answer = answer
        self.calls: list[tuple[str, list[RetrievedChunk]]] = []

    def generate_answer(self, question: str, chunks: list[RetrievedChunk]) -> GeneratedAnswer:
        self.calls.append((question, chunks))
        return self._answer


# --- pure helpers --------------------------------------------------------------


def test_to_retrieved_chunk_drops_rerank_score() -> None:
    chunk = _make_reranked_chunk(chunk_id="A", distance=0.1, rerank_score=0.9)

    result = _to_retrieved_chunk(chunk)

    assert "rerank_score" not in result
    assert result["chunk_id"] == "A"
    assert result["distance"] == 0.1


def test_merge_without_duplicates_keeps_kept_chunks_first_and_drops_duplicates() -> None:
    kept = [_make_reranked_chunk(chunk_id="A", distance=0.1, rerank_score=0.9)]
    new = [
        _make_reranked_chunk(chunk_id="A", distance=0.2, rerank_score=0.5),  # duplicate
        _make_reranked_chunk(chunk_id="B", distance=0.3, rerank_score=0.4),
    ]

    merged = _merge_without_duplicates(kept, new)

    assert [chunk["chunk_id"] for chunk in merged] == ["A", "B"]
    assert merged[0]["rerank_score"] == 0.9  # the kept version survives, not new's


# --- sufficient route ----------------------------------------------------------


def test_sufficient_route_answers_on_the_first_attempt_without_reformulating() -> None:
    retriever = _FakeRetriever(
        [
            [
                _make_retrieved_chunk(chunk_id="A", distance=0.1),
                _make_retrieved_chunk(chunk_id="B", distance=0.2),
            ]
        ]
    )
    reranker = _FakeReranker()
    grader = _FakeGrader(
        [
            EvidenceGrade(
                route="sufficient",
                covered_aspects=["x"],
                missing_aspects=[],
                useful_chunk_ids=["A"],
                rationale="A answers it",
            )
        ]
    )
    reformulator = _FakeReformulator([])
    expected_answer = GeneratedAnswer(answer="15 days", citations=[], abstained=False)
    generator = _FakeGenerator(expected_answer)

    graph = _build_graph(
        retrieve=retriever, reranker=reranker, grader=grader, reformulator=reformulator,
        generator=generator,
    )
    final_state: CragState = graph.invoke(_initial_state("question"))
    result = _to_crag_result(final_state)

    assert result["answer"] == expected_answer
    assert result["retrieval_count"] == 1
    assert reformulator.calls == []
    assert len(generator.calls) == 1
    _, evidence = generator.calls[0]
    assert [chunk["chunk_id"] for chunk in evidence] == ["A"]

    attempt = result["attempts"][0]
    assert attempt["route"] == "sufficient"
    assert attempt["kept_chunk_ids"] == ["A"]
    assert attempt["discarded_chunk_ids"] == ["B"]


# --- ambiguous route: keeps useful evidence, reformulates, dedups --------------


def test_ambiguous_route_keeps_useful_evidence_and_dedups_on_the_next_search() -> None:
    retriever = _FakeRetriever(
        [
            [
                _make_retrieved_chunk(chunk_id="A", distance=0.1),
                _make_retrieved_chunk(chunk_id="B", distance=0.3),
            ],
            [
                _make_retrieved_chunk(chunk_id="A", distance=0.05),
                _make_retrieved_chunk(chunk_id="C", distance=0.2),
            ],
        ]
    )
    reranker = _FakeReranker()
    grader = _FakeGrader(
        [
            EvidenceGrade(
                route="ambiguous",
                covered_aspects=["partial"],
                missing_aspects=["coverage of X"],
                useful_chunk_ids=["A"],
                rationale="A is useful but incomplete",
            ),
            EvidenceGrade(
                route="sufficient",
                covered_aspects=["partial", "X"],
                missing_aspects=[],
                useful_chunk_ids=["A", "C"],
                rationale="now complete",
            ),
        ]
    )
    reformulator = _FakeReformulator(["reformulated query"])
    expected_answer = GeneratedAnswer(answer="answer", citations=[], abstained=False)
    generator = _FakeGenerator(expected_answer)

    graph = _build_graph(
        retrieve=retriever, reranker=reranker, grader=grader, reformulator=reformulator,
        generator=generator,
    )
    result = _to_crag_result(graph.invoke(_initial_state("question")))

    assert result["retrieval_count"] == 2
    assert retriever.queries == ["question", "reformulated query"]
    assert reformulator.calls[0]["missing_aspects"] == ["coverage of X"]

    # The second grading call's pool must contain A exactly once (deduped
    # against the carried-over chunk from round 1), plus the new C.
    _, second_pool = grader.calls[1]
    assert sorted(chunk["chunk_id"] for chunk in second_pool) == ["A", "C"]

    _, evidence = generator.calls[0]
    assert sorted(chunk["chunk_id"] for chunk in evidence) == ["A", "C"]


# --- insufficient route: discards rejected context even if the grader is wrong -


def test_insufficient_route_discards_all_context_even_if_grader_flags_something_useful() -> None:
    retriever = _FakeRetriever(
        [
            [_make_retrieved_chunk(chunk_id="A", distance=0.1)],
            [_make_retrieved_chunk(chunk_id="B", distance=0.1)],
        ]
    )
    reranker = _FakeReranker()
    grader = _FakeGrader(
        [
            # route="insufficient" must force-discard, even though
            # useful_chunk_ids is (incorrectly) non-empty here.
            EvidenceGrade(
                route="insufficient",
                covered_aspects=[],
                missing_aspects=["everything"],
                useful_chunk_ids=["A"],
                rationale="actually nothing useful",
            ),
            EvidenceGrade(
                route="sufficient",
                covered_aspects=["everything"],
                missing_aspects=[],
                useful_chunk_ids=["B"],
                rationale="B answers it",
            ),
        ]
    )
    reformulator = _FakeReformulator(["second query"])
    expected_answer = GeneratedAnswer(answer="answer", citations=[], abstained=False)
    generator = _FakeGenerator(expected_answer)

    graph = _build_graph(
        retrieve=retriever, reranker=reranker, grader=grader, reformulator=reformulator,
        generator=generator,
    )
    result = _to_crag_result(graph.invoke(_initial_state("question")))

    assert result["attempts"][0]["kept_chunk_ids"] == []
    assert result["attempts"][0]["discarded_chunk_ids"] == ["A"]

    # Round 2's pool must only contain B — A was discarded, never carried.
    _, second_pool = grader.calls[1]
    assert [chunk["chunk_id"] for chunk in second_pool] == ["B"]

    _, evidence = generator.calls[0]
    assert [chunk["chunk_id"] for chunk in evidence] == ["B"]


# --- hallucinated useful_chunk_id is never carried forward (defense in depth) --


def test_a_useful_chunk_id_not_in_the_pool_is_silently_dropped() -> None:
    retriever = _FakeRetriever(
        [
            [_make_retrieved_chunk(chunk_id="A", distance=0.1)],
            [_make_retrieved_chunk(chunk_id="B", distance=0.1)],
        ]
    )
    reranker = _FakeReranker()
    grader = _FakeGrader(
        [
            EvidenceGrade(
                route="ambiguous",
                covered_aspects=[],
                missing_aspects=["x"],
                useful_chunk_ids=["does-not-exist-in-pool"],
                rationale="hallucinated id",
            ),
            EvidenceGrade(
                route="sufficient",
                covered_aspects=["x"],
                missing_aspects=[],
                useful_chunk_ids=["B"],
                rationale="B answers it",
            ),
        ]
    )
    reformulator = _FakeReformulator(["second query"])
    generator = _FakeGenerator(GeneratedAnswer(answer="answer", citations=[], abstained=False))

    graph = _build_graph(
        retrieve=retriever, reranker=reranker, grader=grader, reformulator=reformulator,
        generator=generator,
    )
    result = _to_crag_result(graph.invoke(_initial_state("question")))

    assert result["attempts"][0]["kept_chunk_ids"] == []
    _, second_pool = grader.calls[1]
    assert [chunk["chunk_id"] for chunk in second_pool] == ["B"]


# --- "sufficient" with zero surviving evidence is treated as insufficient ------


def test_sufficient_route_with_no_evidence_surviving_the_filter_never_calls_the_generator() -> (
    None
):
    """A grader implementation other than ClaudeEvidenceGrader (which
    already guards against this itself) could return route="sufficient"
    alongside useful_chunk_ids that resolve to nothing in the pool — the
    graph itself must still refuse to answer on zero evidence, and the
    trace's route must reflect that, not the grader's raw claim.
    """
    retriever = _FakeRetriever(
        [
            [_make_retrieved_chunk(chunk_id="A", distance=0.1)],
            [_make_retrieved_chunk(chunk_id="B", distance=0.1)],
        ]
    )
    reranker = _FakeReranker()
    grader = _FakeGrader(
        [
            # Contradictory on purpose: route="sufficient" but the only
            # "useful" id doesn't exist in the pool at all.
            EvidenceGrade(
                route="sufficient",
                covered_aspects=["x"],
                missing_aspects=[],
                useful_chunk_ids=["does-not-exist-in-pool"],
                rationale="claims sufficiency with no real evidence",
            ),
            EvidenceGrade(
                route="sufficient",
                covered_aspects=["x"],
                missing_aspects=[],
                useful_chunk_ids=["B"],
                rationale="B genuinely answers it",
            ),
        ]
    )
    reformulator = _FakeReformulator(["second query"])
    generator = _FakeGenerator(GeneratedAnswer(answer="answer", citations=[], abstained=False))

    graph = _build_graph(
        retrieve=retriever, reranker=reranker, grader=grader, reformulator=reformulator,
        generator=generator,
    )
    result = _to_crag_result(graph.invoke(_initial_state("question")))

    first_attempt = result["attempts"][0]
    assert first_attempt["route"] == "insufficient"  # not the grader's raw "sufficient"
    assert first_attempt["kept_chunk_ids"] == []
    assert len(reformulator.calls) == 1  # continued instead of answering

    # Only round 2's genuinely-grounded answer is ever generated.
    assert len(generator.calls) == 1
    _, evidence = generator.calls[0]
    assert [chunk["chunk_id"] for chunk in evidence] == ["B"]


# --- strict three-retrieval limit and abstention --------------------------------


def test_strict_three_retrieval_limit_then_abstains_on_persistent_ambiguity() -> None:
    retriever = _FakeRetriever(
        [
            [_make_retrieved_chunk(chunk_id="A", distance=0.1)],
            [_make_retrieved_chunk(chunk_id="B", distance=0.1)],
            [_make_retrieved_chunk(chunk_id="C", distance=0.1)],
        ]
    )
    reranker = _FakeReranker()
    ambiguous_grade = EvidenceGrade(
        route="ambiguous",
        covered_aspects=[],
        missing_aspects=["still missing"],
        useful_chunk_ids=[],
        rationale="never quite enough",
    )
    grader = _FakeGrader([ambiguous_grade, ambiguous_grade, ambiguous_grade])
    reformulator = _FakeReformulator(["query 2", "query 3"])
    generator = _FakeGenerator(GeneratedAnswer(answer="unused", citations=[], abstained=False))

    graph = _build_graph(
        retrieve=retriever, reranker=reranker, grader=grader, reformulator=reformulator,
        generator=generator,
    )
    result = _to_crag_result(graph.invoke(_initial_state("question")))

    assert len(retriever.queries) == MAX_RETRIEVALS == 3
    assert len(reformulator.calls) == 2
    assert generator.calls == []
    assert result["retrieval_count"] == 3
    assert result["answer"]["abstained"] is True
    assert result["answer"]["citations"] == []


def test_strict_three_retrieval_limit_then_abstains_on_persistent_insufficiency() -> None:
    retriever = _FakeRetriever(
        [
            [_make_retrieved_chunk(chunk_id="A", distance=0.1)],
            [_make_retrieved_chunk(chunk_id="B", distance=0.1)],
            [_make_retrieved_chunk(chunk_id="C", distance=0.1)],
        ]
    )
    reranker = _FakeReranker()
    insufficient_grade = EvidenceGrade(
        route="insufficient",
        covered_aspects=[],
        missing_aspects=["still missing"],
        useful_chunk_ids=[],
        rationale="never any real evidence",
    )
    grader = _FakeGrader([insufficient_grade, insufficient_grade, insufficient_grade])
    reformulator = _FakeReformulator(["query 2", "query 3"])
    generator = _FakeGenerator(GeneratedAnswer(answer="unused", citations=[], abstained=False))

    graph = _build_graph(
        retrieve=retriever, reranker=reranker, grader=grader, reformulator=reformulator,
        generator=generator,
    )
    result = _to_crag_result(graph.invoke(_initial_state("question")))

    assert len(retriever.queries) == MAX_RETRIEVALS == 3
    assert len(reformulator.calls) == 2
    assert generator.calls == []
    assert result["retrieval_count"] == 3
    assert result["answer"]["abstained"] is True
    assert result["answer"]["citations"] == []

    # Nothing is ever carried forward between attempts: each grading call's
    # pool contains only that attempt's own new candidate, never an
    # earlier attempt's already-rejected chunk.
    assert [chunk["chunk_id"] for _, pool in grader.calls for chunk in pool] == ["A", "B", "C"]
    assert all(attempt["kept_chunk_ids"] == [] for attempt in result["attempts"])


# --- isolation between independent calls ---------------------------------------


def test_two_independent_graph_invocations_never_share_state() -> None:
    def _run(chunk_id: str) -> list[str]:
        retriever = _FakeRetriever([[_make_retrieved_chunk(chunk_id=chunk_id, distance=0.1)]])
        grader = _FakeGrader(
            [
                EvidenceGrade(
                    route="sufficient",
                    covered_aspects=["x"],
                    missing_aspects=[],
                    useful_chunk_ids=[chunk_id],
                    rationale="ok",
                )
            ]
        )
        generator = _FakeGenerator(GeneratedAnswer(answer="a", citations=[], abstained=False))
        graph = _build_graph(
            retrieve=retriever,
            reranker=_FakeReranker(),
            grader=grader,
            reformulator=_FakeReformulator([]),
            generator=generator,
        )
        result = _to_crag_result(graph.invoke(_initial_state("question")))
        assert result["attempts"][0]["kept_chunk_ids"] == [chunk_id]
        _, evidence = generator.calls[0]
        return [chunk["chunk_id"] for chunk in evidence]

    first_evidence = _run("ES-001:1.0:0")
    second_evidence = _run("MX-001:1.0:0")

    assert first_evidence == ["ES-001:1.0:0"]
    assert second_evidence == ["MX-001:1.0:0"]
