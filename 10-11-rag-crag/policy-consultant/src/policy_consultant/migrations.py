"""Simple SQL migration runner: applies numbered .sql files from a
directory in filename order, recording each one in schema_migrations.
No ORM, no migration framework — just ordered files and a ledger table
that is itself the first migration.

Requires a connection in autocommit mode. With autocommit=False, running
a plain query (e.g. the ledger lookup below) before entering
conn.transaction() leaves an implicit transaction open; conn.transaction()
would then open a savepoint inside it instead of a real transaction, and
exiting that block would never actually COMMIT to disk — verified
directly against a running PostgreSQL instance before writing this.
Autocommit avoids this: every statement outside of a transaction() block
commits immediately, so conn.transaction() always starts a genuine
top-level transaction.
"""

from __future__ import annotations

from pathlib import Path

import psycopg


def apply_migrations(migrations_dir: Path, conn: psycopg.Connection) -> list[str]:
    """Apply every pending .sql file in migrations_dir, in filename order.

    Each file's SQL and its ledger entry commit together in one
    transaction; a failing file is never recorded, and no later file is
    attempted. Returns the filenames applied during this call, in order
    (empty if none were pending).
    """
    if not conn.autocommit:
        raise ValueError("apply_migrations requires a connection in autocommit mode")

    applied = _load_applied_filenames(conn)
    pending = sorted(
        path for path in migrations_dir.glob("*.sql") if path.name not in applied
    )

    newly_applied = []
    for path in pending:
        migration_sql = path.read_text(encoding="utf-8")
        with conn.transaction():
            # psycopg's execute() is typed to require a static LiteralString,
            # to deter building SQL from untrusted runtime strings. sql.SQL()
            # doesn't help here either — its own constructor has the same
            # restriction, by design (it's documented for constant template
            # snippets, not arbitrary dynamic content). This string is read
            # from a project-controlled migrations/ file, never from user or
            # LLM input, so this is a deliberate, narrow exception.
            conn.execute(migration_sql)  # pyright: ignore[reportCallIssue, reportArgumentType]
            conn.execute(
                "INSERT INTO schema_migrations (filename) VALUES (%s)",
                (path.name,),
            )
        newly_applied.append(path.name)

    return newly_applied


def _load_applied_filenames(conn: psycopg.Connection) -> set[str]:
    row = conn.execute("SELECT to_regclass('public.schema_migrations') IS NOT NULL").fetchone()
    assert row is not None
    ledger_exists = row[0]

    if not ledger_exists:
        existing_tables = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        ).fetchall()
        if existing_tables:
            names = ", ".join(row[0] for row in existing_tables)
            raise RuntimeError(
                "schema_migrations does not exist, but the 'public' schema "
                f"already contains tables ({names}). Refusing to apply "
                "migrations against a database in an unknown state."
            )
        return set()

    rows = conn.execute("SELECT filename FROM schema_migrations").fetchall()
    return {row[0] for row in rows}
