# Policy Consultant — RAG & CRAG

An AI-powered policy assistant for **Northfern Technologies**, a fictional multinational company operating in Spain, Mexico, and England.

The project explores how Retrieval-Augmented Generation (RAG) and Corrective RAG (CRAG) can provide evidence-grounded answers to employee questions while respecting country-specific policies and role-based access restrictions.

## Current Status

**Phase 1 — Policy corpus completed**

- 12 fictional corporate policy documents, plus one superseded version retained for document-versioning test cases.
- Country-specific and global policies in Spanish and English.
- Different access levels for employees, managers, and HR.
- Structured corpus manifest (`config/corpus-manifest.yaml`) with automated validation (`scripts/validate_manifest.py`).

## Planned Features

- Document retrieval with country and role-based authorization.
- RAG with source citations.
- Corrective RAG for evaluating retrieved evidence.
- Authorized read-only SQL queries for employee-specific information.
- Evaluation of retrieval quality, groundedness, and access restrictions.

## Project Structure

- `data/corpus/` — Corporate policy documents (current versions).
- `data/archive/` — Superseded document versions, retained for versioning test cases.
- `config/` — Structured corpus manifest (scope, access roles, versioning metadata).
- `scripts/` — Corpus maintenance and validation tooling.
- `docs/` — Company background and corpus design documentation.

## Validate the Corpus

```bash
uv sync
uv run python scripts/validate_manifest.py
uv run python -m pytest -q
```

Checks that every document in the manifest resolves to a real file and that its country, role, and version metadata are internally consistent.

Run the pytest suite to verify the manifest validation rules, including access roles, lifecycle dates, and document versioning.

## Disclaimer

All company information, policies, and employee data used in this project are fictional.
