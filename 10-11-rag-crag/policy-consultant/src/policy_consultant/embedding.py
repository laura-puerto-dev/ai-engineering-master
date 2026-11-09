"""Embedding generation: a swappable EmbeddingModel contract, a lazy
batched orchestrator over IndexableChunk streams, and the one concrete
implementation used today (BAAI/bge-m3 via sentence-transformers, running
locally on a single reused model instance).

sentence-transformers and torch are imported lazily, inside
LocalBgeM3EmbeddingModel.__init__, never at module level: importing this
module to use EmbeddingModel or embed_indexable_chunks with a test double
must not require those heavy, GPU-aware dependencies to be installed.
"""

import math
from collections.abc import Iterator
from itertools import batched
from typing import Protocol, cast

from policy_consultant.models import EmbeddedChunk, IndexableChunk


class EmbeddingModel(Protocol):
    """Anything that can turn a batch of texts into a batch of vectors,
    one per text and in the same order, satisfies this contract — no base
    class or registration required to substitute a different provider.
    """

    @property
    def model_id(self) -> str: ...

    @property
    def dimensions(self) -> int: ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding per input text, in the same order."""
        ...


def embed_indexable_chunks(
    items: Iterator[IndexableChunk],
    model: EmbeddingModel,
    *,
    batch_size: int,
) -> Iterator[EmbeddedChunk]:
    """Embed a lazy stream of IndexableChunk in batches, reusing the same
    model instance for every batch.

    Lazy between batches: only one batch's chunks and embeddings are held
    in memory at a time, never the whole corpus. It is expected that a
    full batch is embedded before its first result is yielded — inference
    itself is not incremental — but the next batch is never touched until
    the caller asks for more.

    Each batch is fully validated (count, dimensionality, finite values)
    before any of its EmbeddedChunk are yielded, so a bad batch never
    emits a partial result.
    """
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than 0")

    return _iter_embedded_chunks(items, model, batch_size)


def _iter_embedded_chunks(
    items: Iterator[IndexableChunk],
    model: EmbeddingModel,
    batch_size: int,
) -> Iterator[EmbeddedChunk]:
    # strict=False is itertools.batched's default and is what we want here
    # (a short final batch is expected), but the `strict` keyword itself
    # was only added in Python 3.13; this project targets >=3.12.
    for batch in batched(items, batch_size):  # noqa: B911
        texts = [item["chunk"]["text"] for item in batch]
        embeddings = model.embed_batch(texts)

        _validate_batch(
            embeddings,
            expected_count=len(texts),
            expected_dimensions=model.dimensions,
        )

        for item, embedding in zip(batch, embeddings, strict=True):
            yield EmbeddedChunk(
                document=item["document"],
                chunk=item["chunk"],
                embedding=embedding,
                model_id=model.model_id,
            )


def _validate_batch(
    embeddings: list[list[float]],
    *,
    expected_count: int,
    expected_dimensions: int,
) -> None:
    if len(embeddings) != expected_count:
        raise ValueError(f"Expected {expected_count} embeddings, got {len(embeddings)}")

    for index, embedding in enumerate(embeddings):
        if len(embedding) != expected_dimensions:
            raise ValueError(
                f"Embedding {index} has {len(embedding)} dimensions, "
                f"expected {expected_dimensions}"
            )

        if not all(math.isfinite(value) for value in embedding):
            raise ValueError(f"Embedding {index} contains a NaN or infinite value")


class LocalBgeM3EmbeddingModel:
    """Loads BAAI/bge-m3 once via sentence-transformers and keeps it
    resident on the requested device for reuse across many embed_batch
    calls. Embeddings are L2-normalized at generation time, matching how
    bge-m3 is meant to be used for retrieval.
    """

    _MODEL_NAME = "BAAI/bge-m3"
    # Pinned to a specific Hugging Face commit so the exact weights loaded
    # are reproducible and identifiable in index_metadata, rather than
    # silently floating to whatever "main" resolves to at download time.
    # Verified against https://huggingface.co/BAAI/bge-m3 on 2026-11-09.
    _MODEL_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"

    def __init__(self, device: str) -> None:
        try:
            import torch
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers and torch are required for local "
                "embeddings. Install them with: uv sync --extra embeddings"
            ) from exc

        if device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError(
                "device='cuda' was requested but torch reports no CUDA "
                "device is available. Check the PyTorch/CUDA/driver "
                "installation; this does not fall back to CPU silently."
            )

        try:
            self._model = SentenceTransformer(
                self._MODEL_NAME, device=device, revision=self._MODEL_REVISION
            )
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load embedding model '{self._MODEL_NAME}' on device '{device}'"
            ) from exc

        dimensions = self._model.get_embedding_dimension()
        if dimensions is None:
            raise RuntimeError(
                f"Could not determine the embedding dimensionality of '{self._MODEL_NAME}'"
            )
        self._dimensions: int = dimensions

    @property
    def model_id(self) -> str:
        return self._MODEL_NAME

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def revision(self) -> str:
        return self._MODEL_REVISION

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        # encode() has its own internal batch_size (default 32) that would
        # otherwise silently re-split this call's texts a second time,
        # independently of the batch_size embed_indexable_chunks was
        # configured with. Passing len(texts) makes this one call process
        # exactly what it was given as a single internal batch, so there
        # is only ever one, explicit notion of batch size in this pipeline.
        vectors = self._model.encode(
            texts,
            batch_size=len(texts),
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return cast("list[list[float]]", vectors.tolist())
