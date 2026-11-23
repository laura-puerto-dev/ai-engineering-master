"""Corrective RAG (CRAG) orchestration via LangGraph: question ->
(retrieve -> rerank -> grade evidence -> route)* -> answer or abstain.

answer_question_crag() is this module's one public entry point, the CRAG
counterpart of rag.answer_question — same spirit, much more machinery
underneath. It composes retrieval.retrieve_relevant_chunks() (already
RLS-bound by whatever connection the caller passes in, exactly like
rag.py), embedding.EmbeddingModel, reranking.Reranker,
grade_evidence.EvidenceGrader, reformulate.QueryReformulator, and
generation.AnswerGenerator, wiring them together as a LangGraph
StateGraph. It never generates embeddings itself ahead of time (unlike
rag.answer_question, which is handed one pre-computed query_embedding):
CRAG's reformulate step produces new query *text*, which must be
re-embedded before each retrieval, so embedding is this module's own
responsibility this time.

Retrieval is injected as a plain `retrieve: RetrieveFn` callable, not a
Protocol — one function, one signature, nothing else to swap, so a bare
Callable is the simplest honest contract (compare EmbeddingModel/
Reranker/AnswerGenerator, each with multiple members a Protocol class
actually earns its keep for). answer_question_crag() builds the real
`retrieve` from conn/embedding_model/top_k; tests call _build_graph()
directly with a fake one — never a real PostgreSQL connection, per the
CRAG plan's "dobles de retrieval" test requirement.

Hard safety limit: MAX_RETRIEVALS (3) = one initial retrieval + at most
two post-reformulation retries. This is enforced by _route_after_grading
reading state["attempt"], in Python/LangGraph — never by the grader or
reformulator LLM calls deciding to stop on their own.

Every chunk ever seen by this graph comes from the one `retrieve`
closure the caller built from its own RLS-authorized connection; nothing
here can introduce a chunk from anywhere else. Each call to
answer_question_crag builds its own graph and its own fresh initial
state — nothing is cached or reused across calls, so there is no shared
state for one request's evidence to leak into another's (see
_initial_state).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypedDict

import psycopg
from langgraph.graph import END, START, StateGraph

from policy_consultant.embedding import EmbeddingModel
from policy_consultant.generation import AnswerGenerator
from policy_consultant.grade_evidence import EvidenceGrader
from policy_consultant.language import insufficient_evidence_message
from policy_consultant.models import (
    CragAttemptTrace,
    CragCandidate,
    CragResult,
    GeneratedAnswer,
    RerankedChunk,
    RetrievedChunk,
)
from policy_consultant.reformulate import QueryReformulator
from policy_consultant.reranking import MAX_CANDIDATES, Reranker
from policy_consultant.retrieval import retrieve_relevant_chunks

MAX_RETRIEVALS = 3
"""One initial retrieval + at most two reformulated retries, per the
CRAG plan's explicit limit. Checked by _route_after_grading, never by an
LLM call — a grader/reformulator that never agrees evidence is
sufficient still cannot make the graph retrieve a fourth time.
"""

RetrieveFn = Callable[[str], list[RetrievedChunk]]
"""Given a search query's text, return up to MAX_CANDIDATES authorized
chunks, closest first. The real implementation (built by
answer_question_crag) embeds the text and calls
retrieval.retrieve_relevant_chunks() against the caller's RLS-bound
connection; tests substitute a fake with no PostgreSQL involved at all.
"""


class CragState(TypedDict):
    """Internal LangGraph state — never returned to callers (see
    CragResult, this module's actual public result type). Node functions
    return partial dicts (only the keys they change); LangGraph merges
    them by simple overwrite, since no key here uses a custom reducer —
    every list that must accumulate across attempts (kept_chunks, trace)
    is built with an explicit, already-merged value by the node itself.
    """

    question: str
    current_query: str
    attempt: int
    candidates: list[RetrievedChunk]
    reranked: list[RerankedChunk]
    kept_chunks: list[RerankedChunk]
    missing_aspects: list[str]
    route: str | None
    trace: list[CragAttemptTrace]
    final_answer: GeneratedAnswer | None


def _initial_state(question: str) -> CragState:
    return CragState(
        question=question,
        current_query=question,
        attempt=0,
        candidates=[],
        reranked=[],
        kept_chunks=[],
        missing_aspects=[],
        route=None,
        trace=[],
        final_answer=None,
    )


def _to_retrieved_chunk(chunk: RerankedChunk) -> RetrievedChunk:
    """Project a RerankedChunk back down to the plain RetrievedChunk
    shape generation.AnswerGenerator.generate_answer expects — built
    field by field (never **spread, per this project's convention) so
    rerank_score is dropped deliberately, not accidentally: the
    generator's citations are resolved by position in the list it is
    given (see generation.py), not by any field this drops.
    """
    return RetrievedChunk(
        chunk_id=chunk["chunk_id"],
        document_id=chunk["document_id"],
        version=chunk["version"],
        section_path=chunk["section_path"],
        text=chunk["text"],
        distance=chunk["distance"],
    )


def _merge_without_duplicates(
    kept: list[RerankedChunk], new: list[RerankedChunk]
) -> list[RerankedChunk]:
    """Combine evidence carried over from earlier attempts with this
    attempt's reranked candidates, deduplicated by chunk_id — the same
    chunk can easily come back from a second search with a different
    query. `kept` entries are kept first (already-vetted, higher trust)
    and never duplicated by a `new` entry with the same chunk_id.
    """
    seen_chunk_ids = {chunk["chunk_id"] for chunk in kept}
    merged = list(kept)
    for chunk in new:
        if chunk["chunk_id"] in seen_chunk_ids:
            continue
        seen_chunk_ids.add(chunk["chunk_id"])
        merged.append(chunk)
    return merged


def _build_graph(
    *,
    retrieve: RetrieveFn,
    reranker: Reranker,
    grader: EvidenceGrader,
    reformulator: QueryReformulator,
    generator: AnswerGenerator,
) -> Any:
    def retrieve_node(state: CragState) -> dict[str, Any]:
        candidates = retrieve(state["current_query"])
        return {"candidates": candidates, "attempt": state["attempt"] + 1}

    def rerank_node(state: CragState) -> dict[str, Any]:
        reranked = reranker.rerank(state["current_query"], state["candidates"])
        return {"reranked": reranked}

    def grade_node(state: CragState) -> dict[str, Any]:
        pool = _merge_without_duplicates(state["kept_chunks"], state["reranked"])
        grade = grader.grade(state["question"], pool)

        if grade["route"] == "insufficient":
            # Discard the rejected context entirely, per the CRAG plan's
            # "insufficient: descartar el contexto rechazado" rule —
            # enforced here regardless of what useful_chunk_ids says, so
            # a grader bug can never leak rejected evidence forward.
            carried: list[RerankedChunk] = []
        else:
            useful_ids = set(grade["useful_chunk_ids"])
            # Filtering from `pool` (never looking anything up by id) means
            # a useful_chunk_ids entry that isn't actually in this pool —
            # hallucinated or otherwise — can never be carried forward.
            carried = [chunk for chunk in pool if chunk["chunk_id"] in useful_ids]

        effective_route = grade["route"]
        if effective_route == "sufficient" and not carried:
            # Defense in depth: grade_evidence.ClaudeEvidenceGrader already
            # downgrades this exact combination itself (see
            # _to_evidence_grade), but this graph must not rely solely on
            # that one implementation — a different EvidenceGrader must
            # never be able to reach the answer node with zero evidence
            # actually surviving the authorized-pool filter.
            effective_route = "insufficient"

        carried_ids = {chunk["chunk_id"] for chunk in carried}
        discarded_ids = [
            chunk["chunk_id"] for chunk in pool if chunk["chunk_id"] not in carried_ids
        ]
        trace_entry = CragAttemptTrace(
            attempt=state["attempt"],
            query=state["current_query"],
            candidates=[
                CragCandidate(
                    chunk_id=chunk["chunk_id"],
                    distance=chunk["distance"],
                    rerank_score=chunk["rerank_score"],
                )
                for chunk in state["reranked"]
            ],
            kept_chunk_ids=sorted(carried_ids),
            discarded_chunk_ids=discarded_ids,
            coverage=grade,
            route=effective_route,
        )
        return {
            "kept_chunks": carried,
            "missing_aspects": grade["missing_aspects"],
            "route": effective_route,
            "trace": [*state["trace"], trace_entry],
        }

    def reformulate_node(state: CragState) -> dict[str, Any]:
        new_query = reformulator.reformulate(
            question=state["question"],
            previous_query=state["current_query"],
            missing_aspects=state["missing_aspects"],
        )
        return {"current_query": new_query}

    def answer_node(state: CragState) -> dict[str, Any]:
        evidence = [_to_retrieved_chunk(chunk) for chunk in state["kept_chunks"]]
        answer = generator.generate_answer(state["question"], evidence)
        return {"final_answer": answer}

    def abstain_node(state: CragState) -> dict[str, Any]:
        answer = GeneratedAnswer(
            answer=insufficient_evidence_message(state["question"]),
            citations=[],
            abstained=True,
        )
        return {"final_answer": answer}

    def route_after_grading(state: CragState) -> str:
        if state["route"] == "sufficient":
            return "sufficient"
        if state["attempt"] >= MAX_RETRIEVALS:
            return "stop"
        return "continue"

    graph: StateGraph[CragState] = StateGraph(CragState)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("rerank", rerank_node)
    graph.add_node("grade", grade_node)
    graph.add_node("reformulate", reformulate_node)
    graph.add_node("answer", answer_node)
    graph.add_node("abstain", abstain_node)

    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "rerank")
    graph.add_edge("rerank", "grade")
    graph.add_conditional_edges(
        "grade",
        route_after_grading,
        {"sufficient": "answer", "continue": "reformulate", "stop": "abstain"},
    )
    graph.add_edge("reformulate", "retrieve")
    graph.add_edge("answer", END)
    graph.add_edge("abstain", END)

    return graph.compile()


def _to_crag_result(final_state: CragState) -> CragResult:
    answer = final_state["final_answer"]
    assert answer is not None  # every path (answer_node/abstain_node) sets this
    return CragResult(
        answer=answer,
        attempts=final_state["trace"],
        retrieval_count=final_state["attempt"],
    )


def answer_question_crag(
    conn: psycopg.Connection,
    question: str,
    *,
    embedding_model: EmbeddingModel,
    reranker: Reranker,
    grader: EvidenceGrader,
    reformulator: QueryReformulator,
    generator: AnswerGenerator,
    top_k: int = MAX_CANDIDATES,
) -> CragResult:
    """Answer `question` via the CRAG graph, retrieving at most
    MAX_RETRIEVALS times against `conn`'s RLS-authorized context.

    `conn` must come from db.app_connection(...), the same requirement
    retrieval.retrieve_relevant_chunks() already documents — never
    db.admin_connection(). Each call opens no connection of its own and
    builds a fresh graph/state every time, so nothing from one call can
    leak into another (see this module's docstring).
    """

    def retrieve(query: str) -> list[RetrievedChunk]:
        query_embedding = embedding_model.embed_batch([query])[0]
        return retrieve_relevant_chunks(conn, query_embedding, top_k=top_k)

    compiled_graph = _build_graph(
        retrieve=retrieve,
        reranker=reranker,
        grader=grader,
        reformulator=reformulator,
        generator=generator,
    )
    final_state = compiled_graph.invoke(_initial_state(question))
    return _to_crag_result(final_state)
