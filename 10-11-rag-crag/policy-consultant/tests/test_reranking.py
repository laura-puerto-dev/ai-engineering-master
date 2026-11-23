"""Tests for reranking.py — pure logic only, plus one deterministic
constructor-wiring test for LocalQwen3RerankerModel.

Never imports the real transformers or torch: that one
LocalQwen3RerankerModel test injects fake stand-in modules via
sys.modules instead, so it never touches the network or real weights.
Actual inference against the real model is exercised separately by
scripts/smoke_test_reranker.py, run manually — same convention as
test_embedding.py's LocalBgeM3EmbeddingModel test.
"""

from __future__ import annotations

import sys
import types

import pytest

from policy_consultant.models import RetrievedChunk
from policy_consultant.reranking import (
    MAX_CANDIDATES,
    LocalQwen3RerankerModel,
    _build_ranked_chunks,
    _format_pair,
    _validate_candidate_count,
    _validate_max_length,
)


def _make_chunk(
    *, chunk_id: str = "ES-001:1.0:0", document_id: str = "ES-001", distance: float = 0.1
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id=document_id,
        version="1.0",
        section_path=["1. Section"],
        text=f"Text of {chunk_id}",
        distance=distance,
    )


# --- _format_pair ------------------------------------------------------------


def test_format_pair_matches_qwen3_rerankers_documented_content_block() -> None:
    result = _format_pair("Given a query, retrieve passages", "my query", "my document")

    assert result == (
        "<Instruct>: Given a query, retrieve passages\n<Query>: my query\n<Document>: my document"
    )


# --- _validate_candidate_count ------------------------------------------------


def test_validate_candidate_count_accepts_exactly_the_maximum() -> None:
    chunks = [_make_chunk(chunk_id=f"ES-001:1.0:{i}") for i in range(MAX_CANDIDATES)]
    _validate_candidate_count(chunks)  # must not raise


def test_validate_candidate_count_rejects_more_than_the_maximum() -> None:
    chunks = [_make_chunk(chunk_id=f"ES-001:1.0:{i}") for i in range(MAX_CANDIDATES + 1)]
    with pytest.raises(ValueError, match="at most 10"):
        _validate_candidate_count(chunks)


# --- _validate_max_length -----------------------------------------------------


def test_validate_max_length_rejects_a_budget_exactly_equal_to_the_reserved_tokens() -> None:
    """reserved = len(prefix) + len(suffix) = 3 + 3 = 6: a max_length of
    exactly 6 would leave zero tokens for the actual pair content.
    """
    with pytest.raises(ValueError, match="must be greater than"):
        _validate_max_length(max_length=6, prefix_tokens=[1, 2, 3], suffix_tokens=[4, 5, 6])


def test_validate_max_length_rejects_a_budget_smaller_than_the_reserved_tokens() -> None:
    with pytest.raises(ValueError, match="must be greater than"):
        _validate_max_length(max_length=5, prefix_tokens=[1, 2, 3], suffix_tokens=[4, 5, 6])


def test_validate_max_length_accepts_the_smallest_sufficient_budget() -> None:
    # reserved = 6, max_length = 7 leaves exactly 1 token of budget — the
    # minimum that must be accepted.
    _validate_max_length(max_length=7, prefix_tokens=[1, 2, 3], suffix_tokens=[4, 5, 6])


def test_validate_max_length_accepts_a_comfortable_budget() -> None:
    _validate_max_length(max_length=8192, prefix_tokens=[1, 2, 3], suffix_tokens=[4, 5])


# --- _build_ranked_chunks -----------------------------------------------------


def test_build_ranked_chunks_sorts_by_score_descending() -> None:
    chunks = [_make_chunk(chunk_id="A"), _make_chunk(chunk_id="B"), _make_chunk(chunk_id="C")]
    scores = [0.2, 0.9, 0.5]

    ranked = _build_ranked_chunks(chunks, scores)

    assert [chunk["chunk_id"] for chunk in ranked] == ["B", "C", "A"]
    assert [chunk["rerank_score"] for chunk in ranked] == [0.9, 0.5, 0.2]


def test_build_ranked_chunks_keeps_distance_and_rerank_score_distinct() -> None:
    """A chunk's original pgvector distance must survive unchanged
    alongside its new rerank_score — the two are never conflated, even
    when they disagree about which candidate is "closer".
    """
    chunks = [_make_chunk(chunk_id="A", distance=0.45)]
    scores = [0.9]

    ranked = _build_ranked_chunks(chunks, scores)

    assert ranked[0]["distance"] == 0.45
    assert ranked[0]["rerank_score"] == 0.9


def test_build_ranked_chunks_can_disagree_with_the_original_pgvector_order() -> None:
    """The whole point of reranking: a chunk pgvector ranked worse
    (higher distance) can end up first if its rerank_score is higher.
    """
    chunks = [
        _make_chunk(chunk_id="closer-by-distance", distance=0.10),
        _make_chunk(chunk_id="better-by-rerank", distance=0.40),
    ]
    scores = [0.30, 0.95]

    ranked = _build_ranked_chunks(chunks, scores)

    assert ranked[0]["chunk_id"] == "better-by-rerank"


def test_build_ranked_chunks_preserves_every_input_chunk() -> None:
    chunks = [_make_chunk(chunk_id=f"ES-001:1.0:{i}") for i in range(5)]
    scores = [0.1, 0.2, 0.3, 0.4, 0.5]

    ranked = _build_ranked_chunks(chunks, scores)

    assert {chunk["chunk_id"] for chunk in ranked} == {chunk["chunk_id"] for chunk in chunks}
    assert len(ranked) == len(chunks)


# --- LocalQwen3RerankerModel constructor wiring ------------------------------


def test_local_qwen3_reranker_loads_with_padding_side_left_and_the_given_model_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LocalQwen3RerankerModel must request left-padded tokenization (a
    decoder-only model reads its most recent tokens from the right edge
    of a batch) and load whatever model_id it was given — verified by
    injecting bare fake stand-in modules via sys.modules for the
    duration of this test only, never the real transformers/torch.
    """
    captured: dict[str, object] = {}

    class _FakeTokenizer:
        unk_token_id = 0

        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        @classmethod
        def from_pretrained(cls, model_id: str, **kwargs: object) -> _FakeTokenizer:
            captured["model_id"] = model_id
            captured["padding_side"] = kwargs.get("padding_side")
            return cls()

        def convert_tokens_to_ids(self, token: str) -> int:
            return {"yes": 1, "no": 2}[token]

        def encode(self, text: str, **kwargs: object) -> list[int]:
            return [len(text)]

    class _FakeModel:
        @classmethod
        def from_pretrained(cls, model_id: str, **kwargs: object) -> _FakeModel:
            return cls()

        def eval(self) -> _FakeModel:
            return self

        def to(self, device: object) -> _FakeModel:
            return self

    fake_transformers = types.ModuleType("transformers")
    fake_transformers.AutoModelForCausalLM = _FakeModel  # type: ignore[attr-defined]
    fake_transformers.AutoTokenizer = _FakeTokenizer  # type: ignore[attr-defined]

    fake_torch = types.ModuleType("torch")
    fake_torch.float16 = "float16"  # type: ignore[attr-defined]
    fake_torch.float32 = "float32"  # type: ignore[attr-defined]
    fake_torch.cuda = types.SimpleNamespace(is_available=lambda: False)  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "transformers", fake_transformers)
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    reranker = LocalQwen3RerankerModel(device="cpu", model_id="some/fake-reranker")

    assert captured["model_id"] == "some/fake-reranker"
    assert captured["padding_side"] == "left"
    assert reranker.model_id == "some/fake-reranker"

    # rerank() must short-circuit on an empty candidate list before ever
    # touching the (fake) model/tokenizer again.
    assert reranker.rerank("query", []) == []
