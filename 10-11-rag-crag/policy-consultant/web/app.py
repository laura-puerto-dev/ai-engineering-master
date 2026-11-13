"""FastAPI entry point for the Policy Consultant demo web app.

Run locally with:

    uv run uvicorn web.app:app --reload

Exposes the existing RAG pipeline (policy_consultant.rag.answer_question)
over HTTP:

- GET /api/profiles lists the fixed demo profiles.
- POST /api/ask answers a question under a profile's country/role.

There are no sessions, cookies, or authentication: profile_id is
resolved to (country, role) entirely server-side, from the fixed
DEMO_PROFILES list below — the browser never sends country/role
directly, and nothing here treats profile_id as a verified identity.

The UI itself (web/static/index.html, style.css, app.js) is plain
HTML/CSS/JS served as static files from this same app — no separate
frontend server, no build step, no CORS configuration needed.
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TypedDict

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from policy_consultant.corpus_manifest import load_access_model
from policy_consultant.db import admin_connection, app_connection
from policy_consultant.embedding import EmbeddingModel, LocalBgeM3EmbeddingModel
from policy_consultant.generation import AnswerGenerator, ClaudeAnswerGenerator
from policy_consultant.models import AccessModel, Citation
from policy_consultant.persistence import verify_embedding_model_compatibility
from policy_consultant.rag import answer_question

# admin_connection/app_connection read DATABASE_HOST/POSTGRES_DB/etc.
# straight from os.environ and never load .env themselves (see
# generation.py's docstring on this same convention) — every script in
# this project calls load_dotenv() itself, and this module, as the
# process uvicorn imports, is the one that must call it here.
load_dotenv()

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ACCESS_MODEL_PATH = PROJECT_ROOT / "config" / "access-model.yaml"
STATIC_DIR = Path(__file__).resolve().parent / "static"
TOP_K = 5


class DemoProfile(TypedDict):
    label: str
    country: str
    role: str


# Fixed, backend-owned list of demo profiles. Each id is the only thing
# a client ever sends to select one (see AskRequest below) — country
# and role are resolved here, server-side, never accepted as request
# fields.
DEMO_PROFILES: dict[str, DemoProfile] = {
    "spain-employee": DemoProfile(label="España · Empleado", country="spain", role="employee"),
    "spain-manager": DemoProfile(label="España · Manager", country="spain", role="manager"),
    "spain-hr": DemoProfile(label="España · RR. HH.", country="spain", role="hr"),
    "mexico-employee": DemoProfile(label="México · Empleado", country="mexico", role="employee"),
    "england-employee": DemoProfile(
        label="Inglaterra · Empleado", country="england", role="employee"
    ),
}


class ProfileOut(BaseModel):
    id: str
    label: str


class AskRequest(BaseModel):
    # str_strip_whitespace strips before min_length is checked, so a
    # question made entirely of whitespace is rejected as empty rather
    # than accepted as 1+ "blank" characters.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    profile_id: str = Field(min_length=1)
    question: str = Field(min_length=1)


class CitationOut(BaseModel):
    document_id: str
    version: str
    section_path: list[str]
    chunk_id: str
    text: str


class AskResponse(BaseModel):
    answer: str
    abstained: bool
    citations: list[CitationOut]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Loads everything that is expensive or static once, at startup,
    rather than per request — the same boundary rag.py's own docstring
    already documents for verify_embedding_model_compatibility.
    """
    access_model = load_access_model(ACCESS_MODEL_PATH)
    embedding_model = LocalBgeM3EmbeddingModel(device=os.environ.get("EMBEDDING_DEVICE", "cpu"))

    with admin_connection() as conn:
        verify_embedding_model_compatibility(
            conn,
            model_id=embedding_model.model_id,
            revision=embedding_model.revision,
            dimensions=embedding_model.dimensions,
            normalized=True,
        )

    app.state.access_model = access_model
    app.state.embedding_model = embedding_model
    app.state.generator = ClaudeAnswerGenerator(model="claude-sonnet-5", disable_thinking=True)

    yield


app = FastAPI(title="Policy Consultant", lifespan=lifespan)

# "static" also serves index.html itself (via /static/index.html), but
# GET / below is the friendly entry point most visitors actually use.
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/profiles", response_model=list[ProfileOut])
def list_profiles() -> list[ProfileOut]:
    return [
        ProfileOut(id=profile_id, label=profile["label"])
        for profile_id, profile in DEMO_PROFILES.items()
    ]


@app.post("/api/ask", response_model=AskResponse)
def ask(body: AskRequest, request: Request) -> AskResponse:
    profile = DEMO_PROFILES.get(body.profile_id)
    if profile is None:
        raise HTTPException(status_code=400, detail=f"Unknown profile_id: {body.profile_id!r}")

    access_model: AccessModel = request.app.state.access_model
    embedding_model: EmbeddingModel = request.app.state.embedding_model
    generator: AnswerGenerator = request.app.state.generator

    try:
        query_embedding = embedding_model.embed_batch([body.question])[0]

        with app_connection(
            country=profile["country"], role=profile["role"], access_model=access_model
        ) as conn:
            result = answer_question(
                conn,
                body.question,
                query_embedding=query_embedding,
                generator=generator,
                top_k=TOP_K,
            )
            citations = _load_citation_text(conn, result["citations"])
    except Exception as exc:
        # A genuine lack of evidence never reaches this branch:
        # answer_question() returns a normal abstained=True result for
        # that, handled below like any other answer. Only an actual
        # failure (provider error, database error, ...) lands here —
        # the real exception is logged for debugging, but the client
        # only ever sees a generic message.
        logger.exception("Failed to answer question for profile_id=%r", body.profile_id)
        raise HTTPException(status_code=502, detail="Failed to generate an answer") from exc

    return AskResponse(answer=result["answer"], abstained=result["abstained"], citations=citations)


def _load_citation_text(conn: psycopg.Connection, citations: list[Citation]) -> list[CitationOut]:
    """Citation (policy_consultant.models) deliberately omits the full
    chunk text — this re-fetches it by chunk_id inside the same
    RLS-bound connection the citations were produced under, the same
    pattern scripts/smoke_test_rag.py already uses.

    A cited chunk_id that doesn't come back here (never existed, or
    exists but isn't visible under this connection's RLS context) is a
    genuine inconsistency — answer_question() only ever cites chunks it
    just retrieved through this same connection — so this raises rather
    than silently substituting an empty string; the caller's existing
    except Exception already logs and converts this to the generic 502.
    """
    if not citations:
        return []

    chunk_ids = [citation["chunk_id"] for citation in citations]
    rows = conn.execute(
        "SELECT chunk_id, text FROM chunks WHERE chunk_id = ANY(%s)", (chunk_ids,)
    ).fetchall()
    text_by_chunk_id = {row[0]: row[1] for row in rows}

    missing_chunk_ids = [chunk_id for chunk_id in chunk_ids if chunk_id not in text_by_chunk_id]
    if missing_chunk_ids:
        raise RuntimeError(
            f"Cited chunk_id(s) not found or not visible under this RLS "
            f"context: {missing_chunk_ids}"
        )

    return [
        CitationOut(
            document_id=citation["document_id"],
            version=citation["version"],
            section_path=citation["section_path"],
            chunk_id=citation["chunk_id"],
            text=text_by_chunk_id[citation["chunk_id"]],
        )
        for citation in citations
    ]
