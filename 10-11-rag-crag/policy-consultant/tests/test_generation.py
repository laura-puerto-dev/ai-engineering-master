"""Tests for generation.py — pure, no real Anthropic API calls.

A fake `anthropic` module is injected via sys.modules before constructing
ClaudeAnswerGenerator, never the real package — mirrors the pattern
already used for sentence-transformers/torch in test_embedding.py.
"""

from __future__ import annotations

import sys
import types

import pytest

from policy_consultant.generation import (
    SYSTEM_PROMPT,
    AnswerGenerationError,
    ClaudeAnswerGenerator,
    _build_context,
    _resolve_citations,
)
from policy_consultant.models import Citation, RetrievedChunk


def _make_chunk(
    *,
    document_id: str = "ES-001",
    version: str = "1.0",
    section_path: list[str] | None = None,
    text: str = "Chunk text",
    chunk_id: str | None = None,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id if chunk_id is not None else f"{document_id}:{version}:0",
        document_id=document_id,
        version=version,
        section_path=section_path if section_path is not None else ["Section"],
        text=text,
        distance=0.1,
    )


class _FakeParsed:
    def __init__(self, *, answer: str, abstain: bool, cited_indices: list[int]) -> None:
        self.answer = answer
        self.abstain = abstain
        self.cited_indices = cited_indices


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
    """Replaces anthropic.Anthropic with a fake client that never makes a
    network call. `raises` can be any exception instance — including a
    real anthropic.* or pydantic.ValidationError instance built by the
    caller (see the propagation/conversion tests below) — this helper
    doesn't care what kind of exception it is, only that .parse() raises
    it.
    """
    fake_messages = _FakeMessages(response=response, raises=raises)

    class _FakeAnthropic:
        def __init__(self, *args: object, **kwargs: object) -> None:
            self.messages = fake_messages

    fake_module = types.ModuleType("anthropic")
    fake_module.Anthropic = _FakeAnthropic  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "anthropic", fake_module)
    return fake_messages


def _make_generator(
    monkeypatch: pytest.MonkeyPatch,
    *,
    stop_reason: str = "end_turn",
    parsed_output: object = None,
) -> ClaudeAnswerGenerator:
    response = _FakeResponse(stop_reason=stop_reason, parsed_output=parsed_output)
    _install_fake_anthropic(monkeypatch, response=response)
    return ClaudeAnswerGenerator()


# --- _build_context -------------------------------------------------------


def test_build_context_numbers_chunks_in_order() -> None:
    chunks = [
        _make_chunk(document_id="ES-001", text="First"),
        _make_chunk(document_id="GLB-001", text="Second", section_path=["A", "B"]),
    ]

    context = _build_context(chunks)

    assert "[0] document_id=ES-001 version=1.0 section=Section\nFirst" in context
    assert "[1] document_id=GLB-001 version=1.0 section=A / B\nSecond" in context


# --- _resolve_citations ----------------------------------------------------


def test_resolve_citations_drops_out_of_range_indices() -> None:
    chunks = [_make_chunk()]

    citations = _resolve_citations([0, 5, -1], chunks)

    assert citations == [
        Citation(
            document_id="ES-001", version="1.0", section_path=["Section"], chunk_id="ES-001:1.0:0"
        )
    ]


def test_resolve_citations_dedupes_repeated_indices() -> None:
    chunks = [_make_chunk()]

    citations = _resolve_citations([0, 0, 0], chunks)

    assert len(citations) == 1


# --- generate_answer: the full decision table ------------------------------


def test_generate_answer_resolves_a_valid_citation(monkeypatch: pytest.MonkeyPatch) -> None:
    chunk = _make_chunk(document_id="ES-001")
    generator = _make_generator(
        monkeypatch,
        parsed_output=_FakeParsed(answer="You get 15 days.", abstain=False, cited_indices=[0]),
    )

    result = generator.generate_answer("question", [chunk])

    assert result["abstained"] is False
    assert result["answer"] == "You get 15 days."
    assert result["citations"] == [
        Citation(
            document_id="ES-001", version="1.0", section_path=["Section"], chunk_id="ES-001:1.0:0"
        )
    ]


def test_generate_answer_keeps_valid_citations_and_drops_invalid_ones(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chunk = _make_chunk(document_id="ES-001")
    generator = _make_generator(
        monkeypatch,
        parsed_output=_FakeParsed(answer="Answer", abstain=False, cited_indices=[0, 99]),
    )

    result = generator.generate_answer("question", [chunk])

    assert result["abstained"] is False
    assert len(result["citations"]) == 1


def test_generate_answer_forces_abstention_when_cited_indices_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chunk = _make_chunk()
    generator = _make_generator(
        monkeypatch,
        parsed_output=_FakeParsed(
            answer="A confident-sounding answer", abstain=False, cited_indices=[]
        ),
    )

    result = generator.generate_answer("question", [chunk])

    assert result["abstained"] is True
    assert result["citations"] == []
    # The model's ungrounded prose must not survive as the presented answer.
    assert result["answer"] != "A confident-sounding answer"


def test_generate_answer_forces_abstention_when_all_indices_are_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chunk = _make_chunk()
    generator = _make_generator(
        monkeypatch,
        parsed_output=_FakeParsed(answer="Answer", abstain=False, cited_indices=[7, 8]),
    )

    result = generator.generate_answer("question", [chunk])

    assert result["abstained"] is True
    assert result["citations"] == []


def test_generate_answer_abstain_true_clears_any_citations_the_model_attached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chunk = _make_chunk()
    generator = _make_generator(
        monkeypatch,
        parsed_output=_FakeParsed(
            answer="I don't have enough information.", abstain=True, cited_indices=[0]
        ),
    )

    result = generator.generate_answer("question", [chunk])

    assert result["abstained"] is True
    assert result["citations"] == []
    assert result["answer"] == "I don't have enough information."


def test_generate_answer_abstain_true_with_empty_answer_uses_a_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chunk = _make_chunk()
    generator = _make_generator(
        monkeypatch,
        parsed_output=_FakeParsed(answer="   ", abstain=True, cited_indices=[]),
    )

    result = generator.generate_answer("question", [chunk])

    assert result["abstained"] is True
    assert result["answer"]  # non-empty fallback, not the blank string


@pytest.mark.parametrize(
    ("question", "expected_message"),
    [
        (
            "¿Cuántos días de vacaciones tengo?",
            "No se encontró evidencia suficiente para responder con garantías.",
        ),
        (
            "How many vacation days do I have?",
            "Not enough evidence was found to answer with confidence.",
        ),
    ],
)
def test_generate_answer_localizes_the_fallback_when_cited_indices_is_empty(
    monkeypatch: pytest.MonkeyPatch, question: str, expected_message: str
) -> None:
    chunk = _make_chunk()
    generator = _make_generator(
        monkeypatch,
        parsed_output=_FakeParsed(
            answer="A confident-sounding answer", abstain=False, cited_indices=[]
        ),
    )

    result = generator.generate_answer(question, [chunk])

    assert result["abstained"] is True
    assert result["answer"] == expected_message


@pytest.mark.parametrize(
    ("question", "expected_message"),
    [
        (
            "¿Cuántos días de vacaciones tengo?",
            "No se encontró evidencia suficiente para responder con garantías.",
        ),
        (
            "How many vacation days do I have?",
            "Not enough evidence was found to answer with confidence.",
        ),
    ],
)
def test_generate_answer_localizes_the_fallback_when_abstain_true_with_empty_answer(
    monkeypatch: pytest.MonkeyPatch, question: str, expected_message: str
) -> None:
    chunk = _make_chunk()
    generator = _make_generator(
        monkeypatch,
        parsed_output=_FakeParsed(answer="   ", abstain=True, cited_indices=[]),
    )

    result = generator.generate_answer(question, [chunk])

    assert result["abstained"] is True
    assert result["answer"] == expected_message


def test_generate_answer_raises_on_empty_answer_without_abstaining(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chunk = _make_chunk()
    generator = _make_generator(
        monkeypatch,
        parsed_output=_FakeParsed(answer="", abstain=False, cited_indices=[0]),
    )

    with pytest.raises(AnswerGenerationError, match="empty answer"):
        generator.generate_answer("question", [chunk])


def test_generate_answer_raises_on_refusal(monkeypatch: pytest.MonkeyPatch) -> None:
    chunk = _make_chunk()
    generator = _make_generator(monkeypatch, stop_reason="refusal")

    with pytest.raises(AnswerGenerationError, match="refusal"):
        generator.generate_answer("question", [chunk])


def test_generate_answer_raises_on_truncated_output_even_if_parsed_looks_valid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chunk = _make_chunk()
    generator = _make_generator(
        monkeypatch,
        stop_reason="max_tokens",
        parsed_output=_FakeParsed(answer="Looks fine", abstain=False, cited_indices=[0]),
    )

    with pytest.raises(AnswerGenerationError, match="truncated"):
        generator.generate_answer("question", [chunk])


def test_generate_answer_propagates_a_real_rate_limit_error_unwrapped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A provider-level transport error must reach the caller as the
    SDK's own typed exception, not AnswerGenerationError — see
    AnswerGenerationError's docstring for why these stay separate. Builds
    a real anthropic.RateLimitError (via real httpx2 request/response
    objects, per its actual __init__ signature) rather than a generic
    Exception, so this test fails if that class is ever renamed/removed.
    No network call is made — httpx2.Response is constructed directly.
    """
    anthropic = pytest.importorskip("anthropic")
    httpx2 = pytest.importorskip("httpx2")

    chunk = _make_chunk()
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx2.Response(status_code=429, request=request)
    rate_limit_error = anthropic.RateLimitError("rate limited", response=response, body=None)
    _install_fake_anthropic(monkeypatch, raises=rate_limit_error)
    generator = ClaudeAnswerGenerator()

    with pytest.raises(anthropic.RateLimitError):
        generator.generate_answer("question", [chunk])


def test_generate_answer_propagates_a_real_connection_error_unwrapped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same as above for a transport-level failure with no HTTP response
    at all (anthropic.APIConnectionError takes a request, never a
    response — confirmed against the installed SDK's __init__ signature).
    """
    anthropic = pytest.importorskip("anthropic")
    httpx2 = pytest.importorskip("httpx2")

    chunk = _make_chunk()
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    connection_error = anthropic.APIConnectionError(request=request)
    _install_fake_anthropic(monkeypatch, raises=connection_error)
    generator = ClaudeAnswerGenerator()

    with pytest.raises(anthropic.APIConnectionError):
        generator.generate_answer("question", [chunk])


def test_generate_answer_converts_pydantic_validation_error_to_answer_generation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verified directly against the installed SDK before writing the
    fix: messages.parse() validates the model's text against
    output_format with no try/except of its own, so a response that
    doesn't match the schema raises a real pydantic.ValidationError out
    of that call — not some anthropic-specific error. This must be
    translated to AnswerGenerationError, not left to propagate raw.
    """
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
    generator = ClaudeAnswerGenerator()

    with pytest.raises(AnswerGenerationError, match="did not match the expected structure"):
        generator.generate_answer("question", [chunk])


def test_installed_sdk_accepts_the_arguments_our_call_site_uses() -> None:
    """No network call: binds the real, installed SDK's messages.parse()
    signature against exactly the keyword arguments
    ClaudeAnswerGenerator.generate_answer passes it. Catches a
    renamed/removed parameter (model, max_tokens, output_config,
    output_format, system, messages) at test time instead of only at the
    first real call.
    """
    anthropic = pytest.importorskip("anthropic")
    import inspect

    client = anthropic.Anthropic(api_key="sk-fake-for-signature-check-only")
    signature = inspect.signature(client.messages.parse)

    signature.bind(
        model="claude-sonnet-5",
        max_tokens=1024,
        output_config={"effort": "medium"},
        output_format=object,
        system="system prompt",
        messages=[{"role": "user", "content": "hi"}],
    )
    # The disable_thinking=True call site uses this shape instead —
    # verify it separately, since thinking={"type": "disabled"} is never
    # combined with output_config in that branch.
    signature.bind(
        model="claude-sonnet-5",
        max_tokens=1024,
        thinking={"type": "disabled"},
        output_format=object,
        system="system prompt",
        messages=[{"role": "user", "content": "hi"}],
    )


def test_generate_answer_passes_model_effort_and_system_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chunk = _make_chunk()
    messages = _install_fake_anthropic(
        monkeypatch,
        response=_FakeResponse(
            parsed_output=_FakeParsed(answer="A", abstain=False, cited_indices=[0])
        ),
    )
    generator = ClaudeAnswerGenerator(model="claude-sonnet-5", effort="medium", max_tokens=777)

    generator.generate_answer("question", [chunk])

    call = messages.calls[0]
    assert call["model"] == "claude-sonnet-5"
    assert call["output_config"] == {"effort": "medium"}
    assert call["max_tokens"] == 777
    assert call["system"] == SYSTEM_PROMPT
    assert "thinking" not in call


def test_generate_answer_disables_thinking_and_omits_effort_when_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """disable_thinking=True must send thinking={"type": "disabled"} and
    must NOT also send output_config.effort — that combination hasn't
    been verified against a real authenticated call (see
    ClaudeAnswerGenerator's docstring), so it is never sent together.
    """
    chunk = _make_chunk()
    messages = _install_fake_anthropic(
        monkeypatch,
        response=_FakeResponse(
            parsed_output=_FakeParsed(answer="A", abstain=False, cited_indices=[0])
        ),
    )
    generator = ClaudeAnswerGenerator(disable_thinking=True)

    generator.generate_answer("question", [chunk])

    call = messages.calls[0]
    assert call["thinking"] == {"type": "disabled"}
    assert "output_config" not in call


def test_constructor_raises_import_error_when_anthropic_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "anthropic", None)

    with pytest.raises(ImportError, match="uv sync --extra generation"):
        ClaudeAnswerGenerator()
