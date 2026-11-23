"""Tests for reformulate.py — pure, no real Anthropic API calls.

A fake `anthropic` module is injected via sys.modules before constructing
ClaudeQueryReformulator, never the real package — mirrors the pattern
already used in test_generation.py and test_grade_evidence.py.
"""

from __future__ import annotations

import sys
import types

import pytest

from policy_consultant.reformulate import ClaudeQueryReformulator, QueryReformulationError


class _FakeParsedReformulation:
    def __init__(self, *, reformulated_query: str) -> None:
        self.reformulated_query = reformulated_query


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


def test_reformulate_returns_the_stripped_reformulated_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_anthropic(
        monkeypatch,
        response=_FakeResponse(
            parsed_output=_FakeParsedReformulation(reformulated_query="  better query  ")
        ),
    )

    result = ClaudeQueryReformulator().reformulate(
        question="original question",
        previous_query="first query",
        missing_aspects=["aspect A"],
    )

    assert result == "better query"


def test_reformulate_raises_when_identical_to_the_previous_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_anthropic(
        monkeypatch,
        response=_FakeResponse(
            parsed_output=_FakeParsedReformulation(reformulated_query="remote days per week")
        ),
    )

    with pytest.raises(QueryReformulationError, match="identical to the previous"):
        ClaudeQueryReformulator().reformulate(
            question="question",
            previous_query="remote days per week",
            missing_aspects=["role"],
        )


def test_reformulate_raises_when_identical_after_normalizing_whitespace_and_case(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_anthropic(
        monkeypatch,
        response=_FakeResponse(
            parsed_output=_FakeParsedReformulation(reformulated_query="  Remote   DAYS per week ")
        ),
    )

    with pytest.raises(QueryReformulationError, match="identical to the previous"):
        ClaudeQueryReformulator().reformulate(
            question="question",
            previous_query="remote days per week",
            missing_aspects=["role"],
        )


def test_reformulate_accepts_a_genuinely_different_query(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_anthropic(
        monkeypatch,
        response=_FakeResponse(
            parsed_output=_FakeParsedReformulation(
                reformulated_query="remote work policy for managers"
            )
        ),
    )

    result = ClaudeQueryReformulator().reformulate(
        question="question",
        previous_query="remote days per week",
        missing_aspects=["role"],
    )

    assert result == "remote work policy for managers"


def test_reformulate_raises_on_empty_result(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_anthropic(
        monkeypatch,
        response=_FakeResponse(parsed_output=_FakeParsedReformulation(reformulated_query="   ")),
    )

    with pytest.raises(QueryReformulationError, match="empty reformulated query"):
        ClaudeQueryReformulator().reformulate(
            question="question", previous_query="query", missing_aspects=[]
        )


def test_reformulate_raises_on_refusal(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_anthropic(monkeypatch, response=_FakeResponse(stop_reason="refusal"))

    with pytest.raises(QueryReformulationError, match="refusal"):
        ClaudeQueryReformulator().reformulate(
            question="question", previous_query="query", missing_aspects=[]
        )


def test_reformulate_raises_on_truncated_output(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_anthropic(monkeypatch, response=_FakeResponse(stop_reason="max_tokens"))

    with pytest.raises(QueryReformulationError, match="truncated"):
        ClaudeQueryReformulator().reformulate(
            question="question", previous_query="query", missing_aspects=[]
        )


def test_reformulate_converts_pydantic_validation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    pydantic = pytest.importorskip("pydantic")

    class _Probe(pydantic.BaseModel):  # type: ignore[name-defined,misc]
        x: int

    try:
        pydantic.TypeAdapter(_Probe).validate_json("not valid json")
    except pydantic.ValidationError as exc:
        validation_error = exc
    else:
        pytest.fail("expected pydantic to raise ValidationError for malformed JSON")

    _install_fake_anthropic(monkeypatch, raises=validation_error)

    with pytest.raises(QueryReformulationError, match="did not match the expected structure"):
        ClaudeQueryReformulator().reformulate(
            question="question", previous_query="query", missing_aspects=[]
        )


def test_reformulate_passes_question_previous_query_and_missing_aspects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages = _install_fake_anthropic(
        monkeypatch,
        response=_FakeResponse(
            parsed_output=_FakeParsedReformulation(reformulated_query="new query")
        ),
    )

    ClaudeQueryReformulator(model="claude-sonnet-5", effort="low", max_tokens=128).reformulate(
        question="How many remote days?", previous_query="remote days", missing_aspects=["role"]
    )

    call = messages.calls[0]
    assert call["model"] == "claude-sonnet-5"
    assert call["output_config"] == {"effort": "low"}
    assert call["max_tokens"] == 128
    content = call["messages"][0]["content"]  # type: ignore[index]
    assert "How many remote days?" in content
    assert "remote days" in content
    assert "role" in content


def test_constructor_raises_import_error_when_anthropic_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "anthropic", None)

    with pytest.raises(ImportError, match="uv sync --extra generation"):
        ClaudeQueryReformulator()
