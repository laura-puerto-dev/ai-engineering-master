"""Tests for language.py — pure, no dependencies."""

from __future__ import annotations

import pytest

from policy_consultant.language import detect_language, insufficient_evidence_message


@pytest.mark.parametrize(
    "text",
    [
        "¿Cuántos días de vacaciones tengo en España?",
        "¿Cuál es la política de teletrabajo?",
        "Cuantos dias de vacaciones tengo",  # no accents, still caught by the word list
        "Puedo trabajar desde casa",  # no accents, no question marks, no prior stopwords
        "Tengo vacaciones pendientes",
    ],
)
def test_detect_language_recognizes_spanish(text: str) -> None:
    assert detect_language(text) == "es"


@pytest.mark.parametrize(
    "text",
    [
        "What is my vacation entitlement?",
        "What are the internal HR exception-handling procedures?",
        "Does the company pay for a Netflix subscription?",
    ],
)
def test_detect_language_recognizes_english(text: str) -> None:
    assert detect_language(text) == "en"


@pytest.mark.parametrize("text", ["", "   ", "ES-001", "12345"])
def test_detect_language_defaults_to_english_when_ambiguous(text: str) -> None:
    assert detect_language(text) == "en"


def test_insufficient_evidence_message_is_localized_to_spanish() -> None:
    message = insufficient_evidence_message("¿Cuántos días de vacaciones tengo?")
    assert message == "No se encontró evidencia suficiente para responder con garantías."


def test_insufficient_evidence_message_is_localized_to_english() -> None:
    message = insufficient_evidence_message("How many vacation days do I have?")
    assert message == "Not enough evidence was found to answer with confidence."
