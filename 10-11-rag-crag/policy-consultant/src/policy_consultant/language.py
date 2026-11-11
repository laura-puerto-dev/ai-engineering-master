"""Minimal Spanish/English detection for localizing this project's own
fallback strings — not translation, not general-purpose NLP. The corpus
and every piece of user-facing text this project produces only ever need
to distinguish these two languages (see config/access-model.yaml's
`languages` vocabulary: {"es", "en"}), so a small heuristic here is
proportionate — a language-detection dependency would be solving a much
bigger problem than this project actually has.

Shared by generation.py and rag.py so neither duplicates the detection
logic or the bilingual message text: both call
insufficient_evidence_message(question) wherever they need a localized
abstention answer.
"""

from __future__ import annotations

_SPANISH_CHARS = set("áéíóúñÁÉÍÓÚÑ¿¡")

# Deliberately short: only words that are unambiguously Spanish (no
# meaningful English reading), common enough to show up in a real
# question, and still useful even when the question has none of the
# accented characters above (e.g. "Cuantos dias de vacaciones tengo").
_SPANISH_WORDS = {
    "qué",
    "que",
    "cómo",
    "como",
    "cuántos",
    "cuantos",
    "cuántas",
    "cuantas",
    "cuánto",
    "cuanto",
    "cuánta",
    "cuanta",
    "cuál",
    "cual",
    "cuáles",
    "cuales",
    "dónde",
    "donde",
    "según",
    "segun",
    "días",
    "dias",
    "política",
    "politica",
    "empresa",
    "puedo",
    "tengo",
    "trabajar",
    "desde",
    "casa",
    "vacaciones",
    "pendientes",
    "pendiente",
    "permiso",
    "permisos",
}

_INSUFFICIENT_EVIDENCE_MESSAGES = {
    "es": "No se encontró evidencia suficiente para responder con garantías.",
    "en": "Not enough evidence was found to answer with confidence.",
}


def detect_language(text: str) -> str:
    """Return "es" or "en" — the only two languages this project
    currently supports (config/access-model.yaml). Checked in two steps:
    first any Spanish-exclusive character (an immediate, zero-false-
    positive signal), then a small list of unambiguous Spanish words for
    text that happens to have none of those characters.

    Defaults to "en" when the text gives no clear signal either way
    (empty, numbers-only, or a short phrase that reads the same in both
    languages) — a documented, reasonable default, not a silent guess.
    """
    if any(char in _SPANISH_CHARS for char in text):
        return "es"

    words = {word.strip(".,?!¿¡:;\"'").lower() for word in text.split()}
    if words & _SPANISH_WORDS:
        return "es"

    return "en"


def insufficient_evidence_message(question: str) -> str:
    """The shared abstention text for both of this project's "not enough
    evidence" paths — rag.answer_question (zero chunks retrieved at all)
    and generation.ClaudeAnswerGenerator (zero valid citations survive
    resolution) — localized to whichever of the two supported languages
    `question` appears to be written in.
    """
    return _INSUFFICIENT_EVIDENCE_MESSAGES[detect_language(question)]
