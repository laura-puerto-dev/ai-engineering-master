"""Tests for grade_evidence.py — pure, no real Anthropic API calls.

A fake `anthropic` module is injected via sys.modules before constructing
ClaudeEvidenceGrader, never the real package — mirrors the pattern
already used in test_generation.py and test_embedding.py.
"""

from __future__ import annotations

import sys
import types

import pytest

from policy_consultant.grade_evidence import (
    ClaudeEvidenceGrader,
    EvidenceGradingError,
    _resolve_useful_chunk_ids,
)
from policy_consultant.models import RerankedChunk


def _make_chunk(
    *, chunk_id: str = "ES-001:1.0:0", distance: float = 0.1, rerank_score: float = 0.9
) -> RerankedChunk:
    return RerankedChunk(
        chunk_id=chunk_id,
        document_id="ES-001",
        version="1.0",
        section_path=["1. Section"],
        text=f"Text of {chunk_id}",
        distance=distance,
        rerank_score=rerank_score,
    )


# --- _resolve_useful_chunk_ids -------------------------------------------------


def test_resolve_useful_chunk_ids_drops_out_of_range_indices() -> None:
    chunks = [_make_chunk(chunk_id="A")]

    resolved = _resolve_useful_chunk_ids([0, 5, -1], chunks)

    assert resolved == ["A"]


def test_resolve_useful_chunk_ids_dedupes_repeated_indices() -> None:
    chunks = [_make_chunk(chunk_id="A")]

    resolved = _resolve_useful_chunk_ids([0, 0, 0], chunks)

    assert resolved == ["A"]


def test_resolve_useful_chunk_ids_preserves_given_order() -> None:
    chunks = [_make_chunk(chunk_id="A"), _make_chunk(chunk_id="B"), _make_chunk(chunk_id="C")]

    resolved = _resolve_useful_chunk_ids([2, 0], chunks)

    assert resolved == ["C", "A"]


# --- ClaudeEvidenceGrader.grade: empty pool short-circuit ----------------------


def test_grade_returns_insufficient_without_calling_the_model_when_chunks_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_calls: list[object] = []

    class _ExplodingMessages:
        def parse(self, **kwargs: object) -> object:
            captured_calls.append(kwargs)
            raise AssertionError("must not call the model with an empty chunk pool")

    class _FakeAnthropic:
        def __init__(self, *args: object, **kwargs: object) -> None:
            self.messages = _ExplodingMessages()

    fake_module = types.ModuleType("anthropic")
    fake_module.Anthropic = _FakeAnthropic  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "anthropic", fake_module)

    grader = ClaudeEvidenceGrader()
    grade = grader.grade("question", [])

    assert captured_calls == []
    assert grade["route"] == "insufficient"
    assert grade["useful_chunk_ids"] == []


# --- ClaudeEvidenceGrader.grade: decision table via a fake client -------------


class _FakeParsedGrade:
    def __init__(
        self,
        *,
        route: str,
        covered_aspects: list[str] | None = None,
        missing_aspects: list[str] | None = None,
        useful_indices: list[int] | None = None,
        rationale: str = "rationale",
    ) -> None:
        self.route = route
        self.covered_aspects = covered_aspects if covered_aspects is not None else []
        self.missing_aspects = missing_aspects if missing_aspects is not None else []
        self.useful_indices = useful_indices if useful_indices is not None else []
        self.rationale = rationale


class _FakeResponse:
    def __init__(self, *, stop_reason: str = "end_turn", parsed_output: object = None) -> None:
        self.stop_reason = stop_reason
        self.parsed_output = parsed_output


class _FakeMessages:
    def __init__(self, *, response: object = None, raises: BaseException | None = None) -> None:
        self._response = response
        self._raises = raises
        self.calls: list[dict[str, object]] = []

    def parse(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if self._raises is not None:
            raise self._raises
        return self._response


def _install_fake_anthropic(
    monkeypatch: pytest.MonkeyPatch,
    *,
    response: object = None,
    raises: BaseException | None = None,
) -> _FakeMessages:
    fake_messages = _FakeMessages(response=response, raises=raises)

    class _FakeAnthropic:
        def __init__(self, *args: object, **kwargs: object) -> None:
            self.messages = fake_messages

    fake_module = types.ModuleType("anthropic")
    fake_module.Anthropic = _FakeAnthropic  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "anthropic", fake_module)
    return fake_messages


def test_grade_resolves_a_valid_useful_index(monkeypatch: pytest.MonkeyPatch) -> None:
    chunk = _make_chunk(chunk_id="A")
    _install_fake_anthropic(
        monkeypatch,
        response=_FakeResponse(
            parsed_output=_FakeParsedGrade(route="sufficient", useful_indices=[0])
        ),
    )

    grade = ClaudeEvidenceGrader().grade("question", [chunk])

    assert grade["route"] == "sufficient"
    assert grade["useful_chunk_ids"] == ["A"]


def test_grade_downgrades_sufficient_with_no_valid_useful_indices_to_insufficient(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chunk = _make_chunk(chunk_id="A")
    _install_fake_anthropic(
        monkeypatch,
        response=_FakeResponse(
            parsed_output=_FakeParsedGrade(
                route="sufficient", useful_indices=[99], rationale="looked fine"
            )
        ),
    )

    grade = ClaudeEvidenceGrader().grade("question", [chunk])

    assert grade["route"] == "insufficient"
    assert grade["useful_chunk_ids"] == []
    assert "downgraded" in grade["rationale"]


def test_grade_raises_on_refusal(monkeypatch: pytest.MonkeyPatch) -> None:
    chunk = _make_chunk()
    _install_fake_anthropic(monkeypatch, response=_FakeResponse(stop_reason="refusal"))

    with pytest.raises(EvidenceGradingError, match="refusal"):
        ClaudeEvidenceGrader().grade("question", [chunk])


def test_grade_raises_on_truncated_output(monkeypatch: pytest.MonkeyPatch) -> None:
    chunk = _make_chunk()
    _install_fake_anthropic(monkeypatch, response=_FakeResponse(stop_reason="max_tokens"))

    with pytest.raises(EvidenceGradingError, match="truncated"):
        ClaudeEvidenceGrader().grade("question", [chunk])


def test_grade_converts_pydantic_validation_error_to_evidence_grading_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pydantic = pytest.importorskip("pydantic")

    class _Probe(pydantic.BaseModel):  # type: ignore[name-defined,misc]
        x: int

    try:
        pydantic.TypeAdapter(_Probe).validate_json("not valid json")
    except pydantic.ValidationError as exc:
        validation_error = exc
    else:
        pytest.fail("expected pydantic to raise ValidationError for malformed JSON")

    chunk = _make_chunk()
    _install_fake_anthropic(monkeypatch, raises=validation_error)

    with pytest.raises(EvidenceGradingError, match="did not match the expected structure"):
        ClaudeEvidenceGrader().grade("question", [chunk])


def test_grade_passes_model_effort_and_system_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    chunk = _make_chunk()
    messages = _install_fake_anthropic(
        monkeypatch,
        response=_FakeResponse(parsed_output=_FakeParsedGrade(route="insufficient")),
    )

    ClaudeEvidenceGrader(model="claude-sonnet-5", effort="low", max_tokens=256).grade(
        "question", [chunk]
    )

    call = messages.calls[0]
    assert call["model"] == "claude-sonnet-5"
    assert call["output_config"] == {"effort": "low"}
    assert call["max_tokens"] == 256


def test_constructor_raises_import_error_when_anthropic_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "anthropic", None)

    with pytest.raises(ImportError, match="uv sync --extra generation"):
        ClaudeEvidenceGrader()
