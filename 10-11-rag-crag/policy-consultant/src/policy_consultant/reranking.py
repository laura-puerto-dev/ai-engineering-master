"""Local reranking of retrieved chunks, for CRAG's rerank step.

Reranker is a structural Protocol, the same pattern as
embedding.EmbeddingModel and generation.AnswerGenerator: callers depend
on rerank(query, chunks), never on a concrete provider.

LocalQwen3RerankerModel scores each (query, chunk) pair as the model's
own confidence that the answer to "does this document satisfy the
query?" is "yes" — computed from the logits of the literal "yes"/"no"
tokens at the final position of Qwen3-Reranker-0.6B's documented
ChatML prompt (verified directly against the model card on Hugging
Face, not guessed), never from a separate classification head. This is
a relevance *judgment*, not a calibrated probability that a chunk is
sufficient evidence to answer the question — a high score here can
still mean "topically right, substantively incomplete" (see
crag-implementation-plan.md's separate `grade evidence` step, not
implemented yet). It is also a different signal from pgvector's cosine
`distance` (see retrieval.py/models.RetrievedChunk): the two can and do
disagree, which is the entire reason to rerank in the first place —
never substitute one for the other.

torch and transformers are imported lazily, inside
LocalQwen3RerankerModel.__init__, never at module level — same
convention as embedding.LocalBgeM3EmbeddingModel (sentence-transformers/
torch): importing this module to use the Reranker protocol with a test
double must not require those heavy, GPU-aware dependencies to be
installed.
"""

from __future__ import annotations

from typing import Any, Protocol

from policy_consultant.models import RerankedChunk, RetrievedChunk

DEFAULT_RERANKER_MODEL_ID = "Qwen/Qwen3-Reranker-0.6B"
DEFAULT_INSTRUCTION = "Given a question about internal HR policy, retrieve passages that answer it"
MAX_CANDIDATES = 10


class Reranker(Protocol):
    def rerank(self, query: str, chunks: list[RetrievedChunk]) -> list[RerankedChunk]:
        """Return `chunks` re-ordered by relevance to `query`, most
        relevant first. Every input chunk is returned exactly once —
        this never drops or adds candidates, only scores and re-orders
        them (see models.RerankedChunk's rerank_score).
        """
        ...


def _format_pair(instruction: str, query: str, document: str) -> str:
    """Qwen3-Reranker-0.6B's documented <Instruct>/<Query>/<Document>
    content block — the part of the prompt that varies per pair, wrapped
    by LocalQwen3RerankerModel's fixed ChatML prefix/suffix.
    """
    return f"<Instruct>: {instruction}\n<Query>: {query}\n<Document>: {document}"


def _validate_candidate_count(chunks: list[RetrievedChunk]) -> None:
    if len(chunks) > MAX_CANDIDATES:
        raise ValueError(f"rerank() accepts at most {MAX_CANDIDATES} chunks, got {len(chunks)}")


def _validate_max_length(
    max_length: int, prefix_tokens: list[int], suffix_tokens: list[int]
) -> None:
    """The fixed ChatML prefix/suffix (see LocalQwen3RerankerModel.__init__)
    must themselves fit inside max_length with at least one token left
    over for the actual <Instruct>/<Query>/<Document> content — otherwise
    the truncation budget computed in _process_inputs goes to zero or
    negative, which the tokenizer cannot be trusted to handle sanely.
    """
    reserved = len(prefix_tokens) + len(suffix_tokens)
    if max_length <= reserved:
        raise ValueError(
            f"max_length ({max_length}) must be greater than the combined length of the "
            f"fixed prompt prefix and suffix ({reserved} tokens) — otherwise there is no "
            "room left for the <Instruct>/<Query>/<Document> content"
        )


def _build_ranked_chunks(chunks: list[RetrievedChunk], scores: list[float]) -> list[RerankedChunk]:
    """Pairs each chunk with its score (by position — scores must already
    be in the same order as chunks) and sorts descending by score, most
    relevant first. A tie keeps the chunks' original relative order
    (Python's sort is stable), since nothing here justifies reordering
    otherwise.
    """
    ranked = [
        RerankedChunk(
            chunk_id=chunk["chunk_id"],
            document_id=chunk["document_id"],
            version=chunk["version"],
            section_path=chunk["section_path"],
            text=chunk["text"],
            distance=chunk["distance"],
            rerank_score=score,
        )
        for chunk, score in zip(chunks, scores, strict=True)
    ]
    return sorted(ranked, key=lambda chunk: chunk["rerank_score"], reverse=True)


class LocalQwen3RerankerModel:
    """Loads Qwen3-Reranker-0.6B once via transformers and keeps it
    resident on the requested device for reuse across many rerank()
    calls — same lifecycle contract as LocalBgeM3EmbeddingModel and
    ClaudeAnswerGenerator: construct once at process startup, never per
    request.

    model_id/instruction/max_length are constructor parameters, not
    constants, so any of them can change without touching this class's
    logic — same pattern as ClaudeAnswerGenerator's model/effort/
    max_tokens.
    """

    def __init__(
        self,
        *,
        device: str,
        model_id: str = DEFAULT_RERANKER_MODEL_ID,
        instruction: str = DEFAULT_INSTRUCTION,
        max_length: int = 8192,
    ) -> None:
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise ImportError(
                "transformers and torch are required for local reranking. "
                "Install them with: uv sync --extra reranking"
            ) from exc

        if device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError(
                "device='cuda' was requested but torch reports no CUDA "
                "device is available. Check the PyTorch/CUDA/driver "
                "installation; this does not fall back to CPU silently."
            )

        try:
            tokenizer = AutoTokenizer.from_pretrained(model_id, padding_side="left")
            # float16 halves memory/bandwidth on a GPU; on CPU, torch's
            # float16 kernels are often unsupported or much slower than
            # float32, so float32 is used there instead.
            dtype = torch.float16 if device != "cpu" else torch.float32
            # Typed as Any explicitly: torch's real (not stubbed-out)
            # nn.Module.eval()/.to() are themselves only partially
            # annotated, which mypy's strict mode otherwise flags as
            # calling an untyped function even through this already-Any
            # from_pretrained() return value.
            model: Any = AutoModelForCausalLM.from_pretrained(model_id, dtype=dtype)
            model = model.eval().to(device)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load reranker model '{model_id}' on device '{device}'"
            ) from exc

        token_false_id = tokenizer.convert_tokens_to_ids("no")
        token_true_id = tokenizer.convert_tokens_to_ids("yes")
        if token_true_id == tokenizer.unk_token_id or token_false_id == tokenizer.unk_token_id:
            raise RuntimeError(
                f"Tokenizer for '{model_id}' does not have single-token 'yes'/'no' ids"
            )

        # Qwen3-Reranker-0.6B's documented ChatML template: a fixed
        # system instruction plus assistant-turn scaffolding wrap the
        # per-pair content built by _format_pair. Pre-tokenized once
        # here (not per call) since they never change.
        prefix = (
            "<|im_start|>system\nJudge whether the Document meets the requirements based on "
            'the Query and the Instruct provided. Note that the answer can only be "yes" or '
            '"no".<|im_end|>\n<|im_start|>user\n'
        )
        suffix = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"

        self._torch = torch
        self._tokenizer = tokenizer
        self._model = model
        self._device = device
        self._model_id = model_id
        self._instruction = instruction
        self._max_length = max_length
        self._token_true_id = token_true_id
        self._token_false_id = token_false_id
        self._prefix_tokens = tokenizer.encode(prefix, add_special_tokens=False)
        self._suffix_tokens = tokenizer.encode(suffix, add_special_tokens=False)

    @property
    def model_id(self) -> str:
        return self._model_id

    def rerank(self, query: str, chunks: list[RetrievedChunk]) -> list[RerankedChunk]:
        if not chunks:
            return []
        _validate_candidate_count(chunks)

        pairs = [_format_pair(self._instruction, query, chunk["text"]) for chunk in chunks]
        inputs = self._process_inputs(pairs)
        scores = self._compute_scores(inputs)
        return _build_ranked_chunks(chunks, scores)

    def _process_inputs(self, pairs: list[str]) -> dict[str, Any]:
        _validate_max_length(self._max_length, self._prefix_tokens, self._suffix_tokens)
        budget = self._max_length - len(self._prefix_tokens) - len(self._suffix_tokens)
        inputs = self._tokenizer(
            pairs,
            padding=False,
            truncation="longest_first",
            return_attention_mask=False,
            max_length=budget,
        )
        for i, ids in enumerate(inputs["input_ids"]):
            inputs["input_ids"][i] = self._prefix_tokens + ids + self._suffix_tokens
        inputs = self._tokenizer.pad(
            inputs, padding=True, return_tensors="pt", max_length=self._max_length
        )
        return {key: value.to(self._device) for key, value in inputs.items()}

    def _compute_scores(self, inputs: dict[str, Any]) -> list[float]:
        with self._torch.no_grad():
            batch_scores = self._model(**inputs).logits[:, -1, :]
            true_vector = batch_scores[:, self._token_true_id]
            false_vector = batch_scores[:, self._token_false_id]
            batch_scores = self._torch.stack([false_vector, true_vector], dim=1)
            batch_scores = self._torch.nn.functional.log_softmax(batch_scores, dim=1)
            scores = batch_scores[:, 1].exp().tolist()
        return scores
