# Policy Consultant — RAG & CRAG

An AI-powered HR policy assistant for **Northfern Technologies**, a fictional multinational company operating in Spain, Mexico, and England ([company profile](docs/northfern-company-profile.md)).

The project is a portfolio-grade exploration of Retrieval-Augmented Generation (RAG), evolving toward Corrective RAG (CRAG), that answers employee questions with **evidence-grounded, citable answers** while strictly respecting country-specific policies and role-based access restrictions — enforced in PostgreSQL itself via Row-Level Security, not in application code.

All company information, policies, and employee data used in this project are fictional.

## Current Status

A full, working RAG pipeline is implemented, tested, and manually validated against the real corpus with real embeddings and a real LLM call:

- **Corpus**: 12 current fictional policy documents plus one superseded version, in Spanish and English, with country/role scoping ([corpus inventory](docs/corpus-inventory.md)).
- **PostgreSQL + pgvector**: schema, roles, and Row-Level Security policies that enforce country/role authorization at the database level.
- **Embeddings**: BGE-M3 (1024 dimensions), run locally, with a pinned Hugging Face revision for reproducibility.
- **Corpus sync**: an idempotent reconciliation step that only re-embeds documents that actually changed.
- **Retrieval**: pgvector cosine-distance search over an RLS-bound connection — authorization is never a Python-side filter.
- **Generation**: Claude Sonnet 5, with structured outputs and index-based citation resolution so the model can never cite a document it wasn't given.
- **229 automated tests** (94 of them integration tests against a real PostgreSQL instance), plus a manual smoke test against the real corpus and a real Anthropic call (see [Manual validation](#manual-validation--first-real-run) below).

**Not yet implemented**: a FastAPI service, a web frontend, Corrective RAG (CRAG), and automated evaluation of retrieval/groundedness quality. See [Pending work](#pending-work).

## Architecture

```
config/corpus-manifest.yaml + data/corpus/*.md
        │  (ingestion → chunking → embedding)
        ▼
sync_corpus()  ──────────────▶  PostgreSQL (documents, chunks, index_metadata)
  incremental, idempotent          pgvector + Row-Level Security
                                         │
                                         ▼  app_connection(country, role)
                              retrieve_relevant_chunks()
                                         │  RetrievedChunk[]
                                         ▼
                                  answer_question()
                                         │
                                         ▼
                              ClaudeAnswerGenerator
                      (structured output, index-based citations)
                                         │
                                         ▼
                                  GeneratedAnswer
                        (answer, citations, abstained)
```

### Core modules (`src/policy_consultant/`)

| Module | Responsibility |
|---|---|
| `corpus_manifest.py` | Load and validate `config/corpus-manifest.yaml` against the access-control vocabulary (`config/access-model.yaml`). |
| `ingestion.py`, `chunking.py`, `indexing_prep.py` | Turn current policy documents into a lazy stream of structurally-chunked, numbered fragments. |
| `embedding.py` | `EmbeddingModel` protocol + `LocalBgeM3EmbeddingModel`, a pinned-revision local BGE-M3 wrapper. |
| `migrations.py` + `migrations/*.sql` | A minimal, ordered SQL migration runner (no ORM, no migration framework). |
| `db.py` | `admin_connection()` (unrestricted) and `app_connection()` (RLS-bound, authenticated as the read-only `policy_app` role) — the only two ways this project talks to PostgreSQL. |
| `persistence.py` | `persist_document()` — atomic per-document upsert + full chunk replacement; `verify_embedding_model_compatibility()`. |
| `sync.py` | `sync_corpus()` — reconciles the manifest against PostgreSQL: inserts, version updates, metadata-only updates, and safe no-ops, without ever re-embedding an unchanged document. |
| `retrieval.py` | `retrieve_relevant_chunks()` — pgvector cosine-distance search; carries no authorization logic of its own. |
| `generation.py` | `AnswerGenerator` protocol + `ClaudeAnswerGenerator`; citation resolution by index; `AnswerGenerationError`. |
| `rag.py` | `answer_question()` — the thin orchestration tying retrieval and generation together. |
| `language.py` | A small, dependency-free Spanish/English heuristic used to localize the project's own abstention messages. |

## Tech Stack and Key Decisions

- **Python 3.12**, managed with [`uv`](https://docs.astral.sh/uv/).
- **PostgreSQL 17 + pgvector** (via Docker Compose) for storage and vector search — no separate vector database.
- **psycopg 3** for database access, in autocommit mode with explicit `conn.transaction()` blocks for every atomic unit of work. No ORM, no connection pooling.
- **BGE-M3** (via `sentence-transformers`), run locally rather than through a hosted embeddings API, with its exact Hugging Face revision pinned in code for reproducible vectors.
- **Row-Level Security** is the actual authorization mechanism: `policy_app` is a non-superuser, read-only Postgres role bound to policies that filter `documents`/`chunks` by `app.country`/`app.role`. The application layer never implements its own access-control filtering.
- **Anthropic Claude** (Sonnet 5) for generation, via the official `anthropic` SDK, using **structured outputs** (a Pydantic schema passed to `messages.parse()`) so the model's response is schema-validated rather than parsed out of free text.
- **Citations are resolved by index, never by trusting the model's prose.** The model receives a fixed, numbered list of already-authorized chunks and may only report which *numbers* it used; an answer with zero valid citations is never presented as grounded.
- **No framework for framework's sake**: no LangGraph, no generic repository/ORM layers, no connection pools, no NLP dependency for a two-language heuristic. Every abstraction introduced (e.g. the `EmbeddingModel`/`AnswerGenerator` protocols) exists specifically to make the embedding provider or the LLM provider swappable without rewriting callers.

## Project Structure

```
config/                   Corpus manifest and access-control vocabulary (YAML)
data/corpus/              Current policy documents
data/archive/             Superseded document versions (versioning test cases)
docs/                     Company background and corpus design documentation
migrations/               Ordered SQL migrations (schema, roles, RLS, grants)
scripts/                  Runnable entry points (see "Running the Project")
src/policy_consultant/    Application code (see "Core modules" above)
tests/                    Unit tests + integration tests (pytest, marker "integration")
compose.yaml              PostgreSQL + pgvector service
.env.example              All environment variables this project reads
```

## Environment Setup

```bash
# Base install (manifest validation, no DB/embeddings/LLM needed)
uv sync

# Everything needed to sync the corpus and run the full RAG pipeline
uv sync --extra embeddings --extra persistence --extra generation
```

| Extra | Adds | Needed for |
|---|---|---|
| `embeddings` | `sentence-transformers`, `torch` (CUDA 12.6 wheel index) | Running BGE-M3 locally |
| `persistence` | `psycopg[binary]`, `python-dotenv` | Everything that talks to PostgreSQL |
| `generation` | `anthropic` (pydantic comes in transitively) | `ClaudeAnswerGenerator` / `scripts/smoke_test_rag.py` |

Copy `.env.example` to `.env` and fill in the real values:

- PostgreSQL connection settings (`POSTGRES_*`, `DATABASE_*`) and the bootstrap password for the restricted `policy_app` role (`POLICY_APP_PASSWORD`).
- `EMBEDDING_DEVICE` (`cpu` by default; set to `cuda` for a GPU).
- `ANTHROPIC_API_KEY` — only required for `generation.ClaudeAnswerGenerator`. An `ant auth login` profile also works, since `anthropic.Anthropic()` falls back to it automatically. Either way, **this project's own code never reads `.env` implicitly** — every script calls `load_dotenv()` itself, and nothing ever logs or prints the key.

Start PostgreSQL and apply migrations:

```bash
docker compose up -d
uv run python scripts/apply_migrations.py
```

## PostgreSQL, pgvector, BGE-M3, and Access Control

- **Schema** (`migrations/001_schema.sql`): `documents` (one row per policy, reflecting only its current version), `chunks` (`embedding VECTOR(1024)`, foreign-keyed to `documents` with `ON DELETE CASCADE`), and `index_metadata` (a singleton row recording which embedding model/revision/dimensionality built the live index).
- **Roles and RLS** (`migrations/002_security.sql`, `003_policy_app_index_metadata_read.sql`): `policy_consultant_admin` is the unrestricted superuser used for migrations and writes; `policy_app` is a non-superuser, `NOBYPASSRLS` role with `SELECT`-only grants, bound to RLS policies that only return rows matching the session's `app.country`/`app.role` (set via `set_config(..., true)` inside a single transaction — see `db.app_connection()`).
- **`index_metadata`** lets both `persist_document()` (admin) and `verify_embedding_model_compatibility()` (admin **or** app connection) detect a mismatched embedding configuration before writing or serving anything — there is no silent mixing of embeddings from different models/revisions.
- The full schema rationale, versioning policy, and access model are documented in [`docs/corpus-inventory.md`](docs/corpus-inventory.md).

## Corpus Sync, Embeddings, and Retrieval

`scripts/sync_corpus.py` reconciles `config/corpus-manifest.yaml` against PostgreSQL:

```bash
uv run python scripts/sync_corpus.py
```

It is safe to run repeatedly — `sync_corpus()` classifies every document as a new insert, a real version update (only if `effective_from` actually advances — never a downgrade), a metadata-only update (e.g. `allowed_roles`, no re-embedding), unchanged, a rejected stale version, a metadata conflict requiring human review, or missing from the manifest (reported, never silently deleted). Only documents that actually need new embeddings go through BGE-M3 again.

`retrieval.retrieve_relevant_chunks()` runs a parameterized `ORDER BY embedding <=> %s::vector LIMIT %s` query over whatever `app_connection(country=..., role=...)` the caller provides — RLS does all the authorization; the function carries none of its own.

## RAG Flow: Generation, Citations, and Abstention

`rag.answer_question(conn, question, query_embedding=..., generator=..., top_k=...)` is the single entry point:

1. If retrieval returns no chunks at all, the generator is never called — the answer is an immediate, localized abstention.
2. Otherwise, `ClaudeAnswerGenerator` builds a numbered context block from the (already RLS-authorized) chunks, asks Claude for a structured `{answer, abstain, cited_indices}` response, and resolves `cited_indices` back to the real chunks **by position** — an out-of-range or duplicate index is dropped, never trusted.
3. An answer with zero valid citations is never presented as grounded, even if the model didn't flag `abstain`; it is forced into an abstention instead.
4. Abstention messages are localized to the question's language (Spanish or English — see `language.py`) via a minimal heuristic, with no NLP dependency.
5. Errors are never silently swallowed into a fabricated answer, and the two failure categories are kept distinct on purpose:
   - **Transport and rate-limit failures** (connection errors, 5xx, rate limiting, authentication) propagate as the Anthropic SDK's own typed exceptions (e.g. `anthropic.RateLimitError`, `anthropic.APIConnectionError`), unwrapped — a caller can apply the SDK's own retry guidance directly.
   - **Refusals, truncated output, and invalid structured output** (a response that doesn't validate against the expected schema) are raised as `generation.AnswerGenerationError` — these are "the provider answered, but the answer can't be trusted," a different failure mode from a transport problem, and deliberately not the same exception type.

## Running the Project

```bash
# Validate the manifest only (no DB needed)
uv run python scripts/validate_manifest.py

# Apply pending migrations
uv run python scripts/apply_migrations.py

# Sync the corpus into PostgreSQL (safe to re-run)
uv run python scripts/sync_corpus.py

# Manual smoke tests (real BGE-M3 / real Anthropic calls — never part of the automated suite)
uv run python scripts/smoke_test_embedding.py
uv run python scripts/smoke_test_rag.py
```

### Tests

```bash
# Everything that doesn't need PostgreSQL
uv run pytest -m "not integration"

# Everything that does (requires `docker compose up -d` first)
uv run pytest -m integration

# The full suite
uv run pytest
```

As of this writing: **229 tests pass**, **94** of them integration tests against a real PostgreSQL instance — no skipped tests when PostgreSQL is reachable.

## Manual Validation — First Real Run

`scripts/smoke_test_rag.py` was run against the real 163-chunk corpus using real BGE-M3 embeddings and real Claude Sonnet 5 calls (thinking explicitly disabled for this first run), covering Spain/Mexico/England, role-restricted documents, English-language questions, and a question with no real answer in the corpus. All 8 scenarios completed with no errors; every citation returned was verified to be a literal match for its source fragment, and country/role isolation held in every case — the same restricted-document question returned a correct abstention for an `employee` and the real, correctly-cited answer for `hr`.

**This confirms expected behavior on the eight scenarios tested — it is not an exhaustive security validation.** The connection-level RLS guarantees (that an unauthorized chunk can never be retrieved in the first place, even if it would be the closest vector match) are the responsibility of, and are specifically exercised by, the automated integration tests (`tests/test_security.py`, `tests/test_retrieval.py`, `tests/test_rag.py`) — this manual run observed the *outcome* of that enforcement on a handful of real questions, not a systematic re-verification of it.

Two results are worth recording explicitly, since they look like failures but aren't — and each points to a concrete improvement opportunity for a future stage:

- **"How many vacation days do I have in Mexico?" → abstained.** Unlike Spain and England, Mexico's policy (`MX-001`) sets entitlement by a seniority table rather than a single flat number. There is no one correct number to retrieve, so the model correctly declined to invent one rather than guessing — a correct abstention, not a retrieval gap. **Improvement opportunity**: the current design only distinguishes "grounded answer" from "abstain" — there is no middle ground for a *partial* answer when the policy's rule depends on a personal fact the system doesn't have (here, seniority). A future stage could let the model describe the rule itself (e.g. "it depends on your seniority bracket, as follows: ...") instead of abstaining outright when the missing piece is a specific personal detail, not a missing policy.
- **"Does the company pay for a Netflix subscription?" → abstained.** Retrieval did return chunks (it always returns its `top_k` nearest neighbors, relevant or not — there is no empty-result shortcut here), about training budgets, insurance, and travel expenses. The generator recognized that none of them supported an answer about streaming subscriptions and abstained instead of answering from irrelevant context. This specifically validates the generator-level abstention path, not just the zero-evidence shortcut in `rag.answer_question()`. **Improvement opportunity**: abstention here correctly means "the corpus doesn't establish this," but the wording must keep meaning exactly that — "no evidence of X" is not the same claim as "X is false," and a future iteration of the system prompt/evaluation should explicitly guard against an abstention reading as a categorical denial.

## Pending Work

- A FastAPI service exposing `answer_question()` over HTTP.
- A web frontend.
- Corrective RAG (CRAG): grading retrieved evidence before generation, rather than relying solely on the generator's own abstention judgment.
- Automated evaluation of retrieval quality, groundedness, and a RAG-vs-CRAG comparison.

## Disclaimer

Northfern Technologies and all associated people, policies, and employee data are entirely fictional, used for portfolio and learning purposes only.
