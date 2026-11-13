"""Tests for the static UI (web/static/) being served by this app.

Covers only that FastAPI serves the page and its assets correctly, and
that the hand-written JS still references the same field names as the
Pydantic contract in web/app.py. There is no JS runtime or browser
here, so app.js is never executed — the actual chat flow (profile
selection, sending a question, rendering citations) is verified
manually in a real browser.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from web.app import app

client = TestClient(app)


def test_index_page_is_served_at_root() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Policy Consultant" in response.text


def test_stylesheet_is_served() -> None:
    response = client.get("/static/style.css")

    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]


def test_script_is_served() -> None:
    response = client.get("/static/app.js")

    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]


def test_index_references_the_script_and_stylesheet() -> None:
    response = client.get("/")

    assert "/static/style.css" in response.text
    assert "/static/app.js" in response.text


def test_script_references_the_ask_request_and_response_fields() -> None:
    """A lightweight guard against the API contract drifting out from
    under the hand-written JS. profile.id/profile.label come from
    ProfileOut; profile_id/question from AskRequest; the rest from
    AskResponse/CitationOut (all in web/app.py).
    """
    script = client.get("/static/app.js").text

    assert "profile_id" in script
    assert "question" in script
    assert "abstained" in script
    assert "citations" in script
    assert "document_id" in script
    assert "section_path" in script
