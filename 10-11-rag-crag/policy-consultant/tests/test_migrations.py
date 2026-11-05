"""Tests for the SQL migration runner.

Split into two tiers:
- Generic runner mechanics, against synthetic .sql files written to
  tmp_path: ordering, idempotency, transactional rollback on failure,
  cross-connection persistence, and the "unknown database state" guard.
  These never touch the project's real schema.
- Schema correctness, applying the real migrations/ directory and
  checking the actual constraints, relationships, and cascades it
  creates.

All tests require a running PostgreSQL instance (see compose.yaml) and
run against the dedicated throwaway database from tests/conftest.py,
never the development database.
"""

from __future__ import annotations

from pathlib import Path

import psycopg
import pytest

from policy_consultant.migrations import apply_migrations

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REAL_MIGRATIONS_DIR = PROJECT_ROOT / "migrations"
LEDGER_SQL = (REAL_MIGRATIONS_DIR / "000_migration_ledger.sql").read_text(encoding="utf-8")


def _write_ledger(migrations_dir: Path) -> None:
    (migrations_dir / "000_migration_ledger.sql").write_text(LEDGER_SQL, encoding="utf-8")


def _scalar(cursor: psycopg.Cursor) -> object:
    row = cursor.fetchone()
    assert row is not None
    return row[0]


# --- Generic runner mechanics -------------------------------------------


def test_ledger_migration_applies_and_registers_on_empty_database(
    pg_connection: psycopg.Connection, tmp_path: Path
) -> None:
    _write_ledger(tmp_path)

    applied = apply_migrations(tmp_path, pg_connection)

    assert applied == ["000_migration_ledger.sql"]
    rows = pg_connection.execute("SELECT filename FROM schema_migrations").fetchall()
    assert [row[0] for row in rows] == ["000_migration_ledger.sql"]


def test_applies_pending_migrations_in_filename_order(
    pg_connection: psycopg.Connection, tmp_path: Path
) -> None:
    _write_ledger(tmp_path)
    (tmp_path / "001_create_a.sql").write_text(
        "CREATE TABLE a (id INT PRIMARY KEY);", encoding="utf-8"
    )
    (tmp_path / "002_create_b.sql").write_text(
        "CREATE TABLE b (id INT REFERENCES a(id));", encoding="utf-8"
    )

    applied = apply_migrations(tmp_path, pg_connection)

    assert applied == ["000_migration_ledger.sql", "001_create_a.sql", "002_create_b.sql"]


def test_second_run_is_idempotent(pg_connection: psycopg.Connection, tmp_path: Path) -> None:
    _write_ledger(tmp_path)
    (tmp_path / "001_create_a.sql").write_text("CREATE TABLE a (id INT);", encoding="utf-8")

    first = apply_migrations(tmp_path, pg_connection)
    second = apply_migrations(tmp_path, pg_connection)

    assert first == ["000_migration_ledger.sql", "001_create_a.sql"]
    assert second == []


def test_failing_migration_is_not_recorded_and_stops_later_ones(
    pg_connection: psycopg.Connection, tmp_path: Path
) -> None:
    _write_ledger(tmp_path)
    (tmp_path / "001_create_a.sql").write_text("CREATE TABLE a (id INT);", encoding="utf-8")
    (tmp_path / "002_broken.sql").write_text("THIS IS NOT VALID SQL;", encoding="utf-8")
    (tmp_path / "003_create_c.sql").write_text("CREATE TABLE c (id INT);", encoding="utf-8")

    with pytest.raises(psycopg.Error):
        apply_migrations(tmp_path, pg_connection)

    rows = pg_connection.execute("SELECT filename FROM schema_migrations").fetchall()
    assert [row[0] for row in rows] == ["000_migration_ledger.sql", "001_create_a.sql"]

    exists_c = _scalar(pg_connection.execute("SELECT to_regclass('public.c') IS NOT NULL"))
    assert exists_c is False

    # Retrying after fixing the broken file picks up exactly where it left off.
    (tmp_path / "002_broken.sql").write_text("CREATE TABLE fixed (id INT);", encoding="utf-8")
    retried = apply_migrations(tmp_path, pg_connection)
    assert retried == ["002_broken.sql", "003_create_c.sql"]


def test_failing_statement_rolls_back_earlier_valid_statements_in_the_same_file(
    pg_connection: psycopg.Connection, tmp_path: Path
) -> None:
    _write_ledger(tmp_path)
    (tmp_path / "001_partial.sql").write_text(
        "CREATE TABLE valid_part (id INT); THIS IS NOT VALID SQL;",
        encoding="utf-8",
    )

    with pytest.raises(psycopg.Error):
        apply_migrations(tmp_path, pg_connection)

    exists_valid_part = _scalar(
        pg_connection.execute("SELECT to_regclass('public.valid_part') IS NOT NULL")
    )
    assert exists_valid_part is False

    rows = pg_connection.execute("SELECT filename FROM schema_migrations").fetchall()
    assert [row[0] for row in rows] == ["000_migration_ledger.sql"]


def test_migrations_persist_and_are_visible_from_a_new_connection(
    pg_connection: psycopg.Connection,
    second_pg_connection: psycopg.Connection,
    tmp_path: Path,
) -> None:
    _write_ledger(tmp_path)
    (tmp_path / "001_create_marker.sql").write_text(
        "CREATE TABLE marker (id INT);", encoding="utf-8"
    )

    apply_migrations(tmp_path, pg_connection)

    exists = _scalar(
        second_pg_connection.execute("SELECT to_regclass('public.marker') IS NOT NULL")
    )
    filenames = [
        row[0]
        for row in second_pg_connection.execute(
            "SELECT filename FROM schema_migrations ORDER BY filename"
        ).fetchall()
    ]

    assert exists is True
    assert filenames == ["000_migration_ledger.sql", "001_create_marker.sql"]


def test_refuses_to_apply_when_ledger_missing_but_tables_exist(
    pg_connection: psycopg.Connection, tmp_path: Path
) -> None:
    pg_connection.execute("CREATE TABLE leftover_from_before (id INT)")

    with pytest.raises(RuntimeError, match="unknown state"):
        apply_migrations(tmp_path, pg_connection)

    ledger_exists = _scalar(
        pg_connection.execute("SELECT to_regclass('public.schema_migrations') IS NOT NULL")
    )
    assert ledger_exists is False


def test_rejects_non_autocommit_connection(
    non_autocommit_pg_connection: psycopg.Connection, tmp_path: Path
) -> None:
    with pytest.raises(ValueError, match="autocommit"):
        apply_migrations(tmp_path, non_autocommit_pg_connection)


# --- Real project schema -------------------------------------------------


def test_real_migrations_create_the_expected_tables(pg_connection: psycopg.Connection) -> None:
    apply_migrations(REAL_MIGRATIONS_DIR, pg_connection)

    for table in ("schema_migrations", "documents", "chunks", "index_metadata"):
        exists = _scalar(
            pg_connection.execute("SELECT to_regclass(%s) IS NOT NULL", (f"public.{table}",))
        )
        assert exists is True, f"expected table {table!r} to exist"


def _insert_sample_document(conn: psycopg.Connection, document_id: str = "ES-001") -> None:
    conn.execute(
        """
        INSERT INTO documents
            (document_id, version, country, language, allowed_roles, effective_from, path)
        VALUES
            (%s, '1.0', 'spain', 'es', ARRAY['employee', 'manager', 'hr'],
             '2026-01-01', 'data/corpus/spain/ES-001.md')
        """,
        (document_id,),
    )


def test_negative_ordinal_is_rejected(pg_connection: psycopg.Connection) -> None:
    apply_migrations(REAL_MIGRATIONS_DIR, pg_connection)
    _insert_sample_document(pg_connection)

    with pytest.raises(psycopg.errors.CheckViolation):
        pg_connection.execute(
            """
            INSERT INTO chunks
                (chunk_id, document_id, ordinal, section_path, text, embedding, model_id)
            VALUES ('ES-001:1.0:-1', 'ES-001', -1, ARRAY[]::text[], 'text', %s, 'fake-model')
            """,
            ([0.0] * 1024,),
        )


def test_chunk_id_must_be_prefixed_by_its_document_id(pg_connection: psycopg.Connection) -> None:
    apply_migrations(REAL_MIGRATIONS_DIR, pg_connection)
    _insert_sample_document(pg_connection)

    with pytest.raises(psycopg.errors.CheckViolation):
        pg_connection.execute(
            """
            INSERT INTO chunks
                (chunk_id, document_id, ordinal, section_path, text, embedding, model_id)
            VALUES ('MX-999:1.0:0', 'ES-001', 0, ARRAY[]::text[], 'text', %s, 'fake-model')
            """,
            ([0.0] * 1024,),
        )


def test_allowed_roles_must_be_non_empty(pg_connection: psycopg.Connection) -> None:
    apply_migrations(REAL_MIGRATIONS_DIR, pg_connection)

    with pytest.raises(psycopg.errors.CheckViolation):
        pg_connection.execute(
            """
            INSERT INTO documents
                (document_id, version, country, language, allowed_roles, effective_from, path)
            VALUES
                ('ES-999', '1.0', 'spain', 'es', ARRAY[]::text[], '2026-01-01', 'x.md')
            """
        )


def test_embedding_dimension_mismatch_is_rejected(pg_connection: psycopg.Connection) -> None:
    apply_migrations(REAL_MIGRATIONS_DIR, pg_connection)
    _insert_sample_document(pg_connection)

    with pytest.raises(psycopg.Error):
        pg_connection.execute(
            """
            INSERT INTO chunks
                (chunk_id, document_id, ordinal, section_path, text, embedding, model_id)
            VALUES ('ES-001:1.0:0', 'ES-001', 0, ARRAY[]::text[], 'text', %s, 'fake-model')
            """,
            ([0.0] * 512,),
        )


def test_deleting_a_document_cascades_to_its_chunks(pg_connection: psycopg.Connection) -> None:
    apply_migrations(REAL_MIGRATIONS_DIR, pg_connection)
    _insert_sample_document(pg_connection)
    pg_connection.execute(
        """
        INSERT INTO chunks
            (chunk_id, document_id, ordinal, section_path, text, embedding, model_id)
        VALUES ('ES-001:1.0:0', 'ES-001', 0, ARRAY[]::text[], 'text', %s, 'fake-model')
        """,
        ([0.0] * 1024,),
    )

    pg_connection.execute("DELETE FROM documents WHERE document_id = 'ES-001'")

    remaining = _scalar(pg_connection.execute("SELECT count(*) FROM chunks"))
    assert remaining == 0


def test_duplicate_ordinal_within_a_document_is_rejected(
    pg_connection: psycopg.Connection,
) -> None:
    apply_migrations(REAL_MIGRATIONS_DIR, pg_connection)
    _insert_sample_document(pg_connection)
    pg_connection.execute(
        """
        INSERT INTO chunks
            (chunk_id, document_id, ordinal, section_path, text, embedding, model_id)
        VALUES ('ES-001:1.0:0', 'ES-001', 0, ARRAY[]::text[], 'text', %s, 'fake-model')
        """,
        ([0.0] * 1024,),
    )

    with pytest.raises(psycopg.errors.UniqueViolation):
        pg_connection.execute(
            """
            INSERT INTO chunks
                (chunk_id, document_id, ordinal, section_path, text, embedding, model_id)
            VALUES ('ES-001:1.0:0-dup', 'ES-001', 0, ARRAY[]::text[], 'other', %s, 'fake-model')
            """,
            ([0.0] * 1024,),
        )


def test_index_metadata_is_a_singleton(pg_connection: psycopg.Connection) -> None:
    apply_migrations(REAL_MIGRATIONS_DIR, pg_connection)

    pg_connection.execute(
        """
        INSERT INTO index_metadata
            (embedding_model_id, embedding_model_revision,
             embedding_dimensions, embeddings_normalized)
        VALUES
            ('BAAI/bge-m3', 'unpinned', 1024, true)
        """
    )

    with pytest.raises(psycopg.errors.UniqueViolation):
        pg_connection.execute(
            """
            INSERT INTO index_metadata
                (embedding_model_id, embedding_model_revision,
                 embedding_dimensions, embeddings_normalized)
            VALUES
                ('other-model', 'unpinned', 768, true)
            """
        )
