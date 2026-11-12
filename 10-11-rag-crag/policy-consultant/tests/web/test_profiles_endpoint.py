"""Tests for GET /api/profiles — no PostgreSQL, no BGE-M3, no Anthropic.

list_profiles() only reads the module-level DEMO_PROFILES constant, so
it needs no app.state and therefore no lifespan — a bare TestClient(app)
(never entered as a context manager) is enough.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from web.app import DEMO_PROFILES, app

client = TestClient(app)


def test_list_profiles_returns_the_five_configured_profiles() -> None:
    response = client.get("/api/profiles")

    assert response.status_code == 200
    profiles = response.json()
    assert {profile["id"] for profile in profiles} == set(DEMO_PROFILES.keys())
    # Only id/label travel over the wire — see web.app.ProfileOut.
    assert set(profiles[0].keys()) == {"id", "label"}


def test_list_profiles_includes_the_expected_labels() -> None:
    response = client.get("/api/profiles")

    labels_by_id = {profile["id"]: profile["label"] for profile in response.json()}
    assert labels_by_id["spain-hr"] == "España · RR. HH."
    assert labels_by_id["mexico-employee"] == "México · Empleado"
