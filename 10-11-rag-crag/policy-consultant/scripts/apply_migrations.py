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

    # Validated here, before it ever reaches SQL, so a missing or blank
    # value fails with a clear message instead of a less obvious error
    # from inside 002_security.sql. Never interpolated into any message.
    policy_app_password = os.environ.get("POLICY_APP_PASSWORD", "")
    if not policy_app_password:
        raise ValueError("POLICY_APP_PASSWORD must be set to a non-empty value")

    conn = psycopg.connect(
        host=os.environ["DATABASE_HOST"],
        port=os.environ["DATABASE_PORT"],
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        autocommit=True,
    )

    try:
        # Only read by 002_security.sql, and only inside its IF NOT EXISTS
        # guard — this never changes an already-created policy_app's
        # password, including on every subsequent run of this script.
        conn.execute(
            "SELECT set_config('app.policy_app_bootstrap_password', %s, false)",
            (policy_app_password,),
        )
        applied = apply_migrations(MIGRATIONS_DIR, conn)
    finally:
        conn.close()

    print("Applied: " + ", ".join(applied) if applied else "Nothing to apply.")


if __name__ == "__main__":
    main()
