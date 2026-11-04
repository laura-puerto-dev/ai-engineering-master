"""Tests for embed_indexable_chunks against a fake EmbeddingModel.

Never imports sentence-transformers or torch: LocalBgeM3EmbeddingModel is
exercised separately by scripts/smoke_test_embedding.py, run manually.
"""

from collections.abc import Callable
from datetime import date

import pytest

from policy_consultant.embedding import embed_indexable_chunks
from policy_consultant.models import DocumentChunk, IndexableChunk, PolicyDocument


class FakeEmbeddingModel:
    """Deterministic stand-in for EmbeddingModel: each embedding is the
    input text's length, repeated across every dimension. Records every
    batch it was called with, so tests can assert on batching and reuse.
    """

    def __init__(self, dimensions: int = 4, model_id: str = "fake-model") -> None:
        self._dimensions = dimensions
        self._model_id = model_id
        self.calls: list[list[str]] = []

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        return [[float(len(text))] * self._dimensions for text in texts]


class ScriptedEmbeddingModel:
    """Returns pre-programmed embeddings regardless of input, to exercise
    _validate_batch's failure paths deterministically."""

    def __init__(self, embeddings: list[list[float]], *, dimensions: int = 4) -> None:
        self._embeddings = embeddings
        self._dimensions = dimensions

    @property
    def model_id(self) -> str:
        return "scripted-model"

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return self._embeddings


@pytest.fixture
def make_indexable_chunk() -> Callable[..., IndexableChunk]:
    def _make(
        *,
        document_id: str = "ES-001",
        ordinal: int = 0,
        text: str = "Some text.",
    ) -> IndexableChunk:
        document = PolicyDocument(
            document_id=document_id,
            path=f"data/corpus/{document_id}.md",
            country="spain",
            language="es",
            allowed_roles=["employee", "manager", "hr"],
            version="1.0",
            effective_from=date(2026, 1, 1),
            effective_to=None,
            status="current",
        )
        chunk = DocumentChunk(
            chunk_id=f"{document_id}:1.0:{ordinal}",
            document_id=document_id,
            ordinal=ordinal,
            section_path=["1. Section"],
            text=text,
        )
        return IndexableChunk(document=document, chunk=chunk)

    return _make


def test_batches_and_reuses_the_same_model_instance(
    make_indexable_chunk: Callable[..., IndexableChunk],
) -> None:
    items = [make_indexable_chunk(ordinal=i, text=f"Text {i}") for i in range(5)]
    model = FakeEmbeddingModel()

    list(embed_indexable_chunks(iter(items), model, batch_size=2))

    assert model.calls == [
        ["Text 0", "Text 1"],
        ["Text 2", "Text 3"],
        ["Text 4"],
    ]


def test_preserves_order_and_associates_chunk_with_document(
    make_indexable_chunk: Callable[..., IndexableChunk],
) -> None:
    items = [
        make_indexable_chunk(document_id="ES-001", ordinal=0, text="aa"),
        make_indexable_chunk(document_id="ES-001", ordinal=1, text="bbbb"),
        make_indexable_chunk(document_id="MX-001", ordinal=0, text="c"),
    ]
    model = FakeEmbeddingModel(dimensions=1)

    results = list(embed_indexable_chunks(iter(items), model, batch_size=10))

    assert [result["chunk"]["text"] for result in results] == ["aa", "bbbb", "c"]
    assert [result["document"]["document_id"] for result in results] == [
        "ES-001",
        "ES-001",
        "MX-001",
    ]
    assert [result["embedding"] for result in results] == [[2.0], [4.0], [1.0]]
    assert all(result["model_id"] == "fake-model" for result in results)


def test_lazy_between_batches(
    make_indexable_chunk: Callable[..., IndexableChunk],
) -> None:
    items = [make_indexable_chunk(ordinal=i, text=f"Text {i}") for i in range(4)]
    model = FakeEmbeddingModel()

    stream = embed_indexable_chunks(iter(items), model, batch_size=2)
    first = next(stream)

    assert len(model.calls) == 1
    assert first["chunk"]["ordinal"] == 0


def test_rejects_batch_with_wrong_embedding_count(
    make_indexable_chunk: Callable[..., IndexableChunk],
) -> None:
    items = [make_indexable_chunk(ordinal=0), make_indexable_chunk(ordinal=1)]
    model = ScriptedEmbeddingModel([[0.0, 0.0, 0.0, 0.0]])

    stream = embed_indexable_chunks(iter(items), model, batch_size=10)

    with pytest.raises(ValueError, match="Expected 2 embeddings, got 1"):
        next(stream)


def test_rejects_embedding_with_wrong_dimensions(
    make_indexable_chunk: Callable[..., IndexableChunk],
) -> None:
    items = [make_indexable_chunk(ordinal=0)]
    model = ScriptedEmbeddingModel([[0.0, 0.0, 0.0]], dimensions=4)

    stream = embed_indexable_chunks(iter(items), model, batch_size=10)

    with pytest.raises(ValueError, match="has 3 dimensions, expected 4"):
        next(stream)


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), float("-inf")])
def test_rejects_non_finite_embedding_values(
    make_indexable_chunk: Callable[..., IndexableChunk],
    bad_value: float,
) -> None:
    items = [make_indexable_chunk(ordinal=0)]
    model = ScriptedEmbeddingModel([[0.0, bad_value, 0.0, 0.0]], dimensions=4)

    stream = embed_indexable_chunks(iter(items), model, batch_size=10)

    with pytest.raises(ValueError, match="NaN or infinite"):
        next(stream)


def test_invalid_batch_yields_nothing_before_raising(
    make_indexable_chunk: Callable[..., IndexableChunk],
) -> None:
    items = [
        make_indexable_chunk(ordinal=0, text="first"),
        make_indexable_chunk(ordinal=1, text="second"),
    ]
    model = ScriptedEmbeddingModel([[0.0, 0.0, 0.0, 0.0]])  # only 1 for 2 texts

    stream = embed_indexable_chunks(iter(items), model, batch_size=10)

    # The very first next() call must raise directly: nothing from this
    # (single, invalid) batch is ever yielded.
    with pytest.raises(ValueError, match="Expected 2 embeddings, got 1"):
        next(stream)

    with pytest.raises(StopIteration):
        next(stream)


@pytest.mark.parametrize("batch_size", [0, -3])
def test_rejects_non_positive_batch_size(
    make_indexable_chunk: Callable[..., IndexableChunk],
    batch_size: int,
) -> None:
    items = [make_indexable_chunk(ordinal=0)]
    model = FakeEmbeddingModel()

    with pytest.raises(ValueError, match="batch_size must be greater than 0"):
        embed_indexable_chunks(iter(items), model, batch_size=batch_size)
