"""CLI entry point: apply pending SQL migrations in migrations/ against
the configured PostgreSQL database.

Connection handling here is intentionally minimal — a single autocommit
connection built directly from environment variables. The reusable
admin/app connection module is introduced in a later persistence stage.
"""

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

from policy_consultant.migrations import apply_migrations

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = PROJECT_ROOT / "migrations"


def main() -> None:
    load_dotenv()

    conn = psycopg.connect(
        host=os.environ["DATABASE_HOST"],
        port=os.environ["DATABASE_PORT"],
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        autocommit=True,
    )

    try:
        applied = apply_migrations(MIGRATIONS_DIR, conn)
    finally:
        conn.close()

    print("Applied: " + ", ".join(applied) if applied else "Nothing to apply.")


if __name__ == "__main__":
    main()
