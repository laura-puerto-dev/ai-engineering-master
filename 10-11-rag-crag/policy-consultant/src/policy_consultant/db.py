"""Short-lived PostgreSQL connections for Policy Consultant.

admin_connection() is unrestricted (policy_consultant_admin) for
migrations and ingestion; app_connection() is RLS-bound (policy_app) for
authorized reads, with app.country/app.role scoped to one explicit
transaction. No pooling, no ORM: every connection here is opened, used,
and closed within a single `with` block.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg

from policy_consultant.models import AccessModel

_GLOBAL_SCOPE = "global"


def _require_env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise ValueError(f"{name} must be set to a non-empty value")
    return value


def _connect(
    dbname: str,
    *,
    user: str,
    password: str,
    autocommit: bool,
    connect_timeout: int | None = None,
) -> psycopg.Connection:
    return psycopg.connect(
        host=_require_env("DATABASE_HOST"),
        port=int(_require_env("DATABASE_PORT")),
        dbname=dbname,
        user=user,
        password=password,
        autocommit=autocommit,
        connect_timeout=connect_timeout,
    )


@contextmanager
def admin_connection(
    *, dbname: str | None = None, connect_timeout: int | None = None
) -> Iterator[psycopg.Connection]:
    """An autocommit connection authenticated as policy_consultant_admin.

    Unrestricted: bypasses row-level security entirely (see
    migrations/002_security.sql — policy_consultant_admin is a
    superuser in this local setup, and would bypass RLS even if it
    weren't). Use conn.transaction() for each atomic unit of work, the
    same way migrations.apply_migrations() already does. Never use this
    connection to serve an end-user-facing read — it has none of
    policy_app's restrictions.

    dbname defaults to POSTGRES_DB; tests pass the dedicated test
    database explicitly instead.
    """
    conn = _connect(
        dbname if dbname is not None else _require_env("POSTGRES_DB"),
        user=_require_env("POSTGRES_USER"),
        password=_require_env("POSTGRES_PASSWORD"),
        autocommit=True,
        connect_timeout=connect_timeout,
    )
    try:
        yield conn
    finally:
        conn.close()


def _validate_app_context(country: str, role: str, access_model: AccessModel) -> None:
    if not role or role not in access_model["roles"]:
        raise ValueError(f"Unrecognized role: {role!r}")
    if not country:
        raise ValueError("country must be a non-empty string")
    if country == _GLOBAL_SCOPE:
        raise ValueError("'global' is a document scope, not a valid user country")
    if country not in access_model["countries"]:
        raise ValueError(f"Unrecognized country: {country!r}")


@contextmanager
def app_connection(
    *,
    country: str,
    role: str,
    access_model: AccessModel,
    dbname: str | None = None,
) -> Iterator[psycopg.Connection]:
    """A single connection, single transaction, authenticated as
    policy_app.

    country and role are validated against access_model before anything
    connects. 'global' is rejected explicitly even though it is a valid
    *document* scope (one of access_model's four country values) — it
    is never a valid *user* country, the same exclusion
    migrations/002_security.sql's access_context_is_set() already
    enforces in SQL. This is deliberately not a second copy of that
    function's full vocabulary: everything else about which countries
    and roles exist still comes from access_model, a single source.

    The connection opens in autocommit mode specifically so the
    `with conn.transaction():` below is unambiguously a real top-level
    transaction and never a nested savepoint inside some earlier
    implicit one (see migrations.py's own docstring, where that
    ambiguity was first verified and ruled out this way).

    app.country and app.role are set with set_config(..., true) inside
    that one transaction, which also contains every query the caller
    runs through the yielded connection — committing or rolling it back
    is what starts and ends the context's lifetime. No connection here
    is ever reused across separate calls: each call to app_connection is
    a fully independent connection and transaction, opened and closed
    within it, so there is no second operation for the context to leak
    into.
    """
    _validate_app_context(country, role, access_model)

    conn = _connect(
        dbname if dbname is not None else _require_env("POSTGRES_DB"),
        user="policy_app",
        password=_require_env("POLICY_APP_PASSWORD"),
        autocommit=True,
    )
    try:
        with conn.transaction():
            conn.execute("SELECT set_config('app.country', %s, true)", (country,))
            conn.execute("SELECT set_config('app.role', %s, true)", (role,))
            yield conn
    finally:
        conn.close()
