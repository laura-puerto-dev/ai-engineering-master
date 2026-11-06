"""CLI entry point: apply pending SQL migrations in migrations/ against
the configured PostgreSQL database.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from policy_consultant.db import admin_connection
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

    with admin_connection() as conn:
        # Only read by 002_security.sql, and only inside its IF NOT EXISTS
        # guard — this never changes an already-created policy_app's
        # password, including on every subsequent run of this script.
        conn.execute(
            "SELECT set_config('app.policy_app_bootstrap_password', %s, false)",
            (policy_app_password,),
        )
        applied = apply_migrations(MIGRATIONS_DIR, conn)

    print("Applied: " + ", ".join(applied) if applied else "Nothing to apply.")


if __name__ == "__main__":
    main()
