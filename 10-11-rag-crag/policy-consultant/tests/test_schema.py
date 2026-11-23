"""Integration tests for the physical schema produced by applying every
real migration (migrations/*.sql, via tests/conftest.py's
policy_app_ready fixture) — as opposed to test_migrations.py, which only
tests apply_migrations()'s own generic ordering/idempotency logic
against synthetic tmp_path migration files, never the real ones.

Verified directly against PostgreSQL's real catalog
(pg_index/pg_am/pg_opclass/pg_attribute), never assumed from a
migration file's own SQL text.
"""

from __future__ import annotations

import psycopg
import pytest

pytestmark = pytest.mark.integration


def test_chunks_embedding_has_an_hnsw_index_with_cosine_ops(
    policy_app_ready: psycopg.Connection,
) -> None:
    row = policy_app_ready.execute(
        """
        SELECT t.relname AS table_name,
               am.amname AS access_method,
               a.attname AS column_name,
               opc.opcname AS operator_class
        FROM pg_index idx
        JOIN pg_class i ON i.oid = idx.indexrelid
        JOIN pg_class t ON t.oid = idx.indrelid
        JOIN pg_am am ON am.oid = i.relam
        JOIN pg_attribute a ON a.attrelid = idx.indrelid AND a.attnum = idx.indkey[0]
        JOIN pg_opclass opc ON opc.oid = idx.indclass[0]
        WHERE i.relname = 'chunks_embedding_hnsw_idx'
        """
    ).fetchone()

    assert row is not None, "chunks_embedding_hnsw_idx does not exist after migrating"
    table_name, access_method, column_name, operator_class = row
    assert table_name == "chunks"
    assert access_method == "hnsw"
    assert column_name == "embedding"
    assert operator_class == "vector_cosine_ops"
