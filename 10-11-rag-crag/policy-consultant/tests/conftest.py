"""Shared fixtures for PostgreSQL integration tests.

Every integration test runs against a dedicated, throwaway database
(TEST_DATABASE_NAME) — never against the development database the
application itself is configured to use. That name is a hardcoded
literal, not read from any .env variable, specifically so a
misconfigured environment cannot redirect a destructive reset at real
project data: pg_connection asserts the connected database's actual
name before running anything destructive.
"""

from __future__ import annotations

import contextlib
import os
from collections.abc import Iterator
from pathlib import Path
from typing import TypedDict

import psycopg
import pytest
from dotenv import load_dotenv
from psycopg import sql

from policy_consultant.migrations import apply_migrations

load_dotenv()

TEST_DATABASE_NAME = "policy_consultant_test"
REAL_MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


class _ConnectionParams(TypedDict):
    host: str
    port: int
    user: str
    password: str


def _connection_params() -> _ConnectionParams:
    return {
        "host": os.environ.get("DATABASE_HOST", "localhost"),
        "port": int(os.environ.get("DATABASE_PORT", "5432")),
        "user": os.environ.get("POSTGRES_USER", "policy_consultant_admin"),
        "password": os.environ.get("POSTGRES_PASSWORD", ""),
    }


def _connect(
    dbname: str,
    *,
    autocommit: bool = False,
    connect_timeout: int | None = None,
    user: str | None = None,
    password: str | None = None,
) -> psycopg.Connection:
    params = _connection_params()
    return psycopg.connect(
        host=params["host"],
        port=params["port"],
        user=user if user is not None else params["user"],
        password=password if password is not None else params["password"],
        dbname=dbname,
        autocommit=autocommit,
        connect_timeout=connect_timeout,
    )


@pytest.fixture(scope="session")
def _test_database_ready() -> None:
    """Create the dedicated test database once per test session, if it
    doesn't already exist. Skips the whole integration suite if
    PostgreSQL isn't reachable, rather than failing.
    """
    try:
        conn = _connect("postgres", autocommit=True, connect_timeout=3)
    except psycopg.OperationalError as exc:
        pytest.skip(f"PostgreSQL is not reachable: {exc}")

    try:
        with contextlib.suppress(psycopg.errors.DuplicateDatabase):
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(TEST_DATABASE_NAME)))
    finally:
        conn.close()


@pytest.fixture
def pg_connection(_test_database_ready: None) -> Iterator[psycopg.Connection]:
    """An autocommit connection to the dedicated test database, reset to
    a blank 'public' schema before the test runs.
    """
    conn = _connect(TEST_DATABASE_NAME, autocommit=True)

    row = conn.execute("SELECT current_database()").fetchone()
    assert row is not None
    actual_database = row[0]
    if actual_database != TEST_DATABASE_NAME:
        conn.close()
        raise RuntimeError(
            f"Refusing to reset database {actual_database!r}: expected the "
            f"dedicated test database {TEST_DATABASE_NAME!r}."
        )

    conn.execute("DROP SCHEMA public CASCADE")
    conn.execute("CREATE SCHEMA public")

    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def second_pg_connection(_test_database_ready: None) -> Iterator[psycopg.Connection]:
    """A second, independent autocommit connection to the same dedicated
    test database — for asserting that changes made via pg_connection are
    genuinely durable, not merely visible within one session.
    """
    conn = _connect(TEST_DATABASE_NAME, autocommit=True)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def non_autocommit_pg_connection(_test_database_ready: None) -> Iterator[psycopg.Connection]:
    """A connection to the dedicated test database in the default
    (non-autocommit) mode, for testing that apply_migrations rejects it.
    """
    conn = _connect(TEST_DATABASE_NAME)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def policy_app_ready(pg_connection: psycopg.Connection) -> psycopg.Connection:
    """Applies the real migrations (through 002_security.sql) against the
    freshly reset test database. policy_app's password is bootstrapped
    from POLICY_APP_PASSWORD only the first time the role is ever created
    cluster-wide; since the role outlives the schema reset between tests,
    later test runs leave an already-set password untouched.

    Returns the admin connection (pg_connection), for seeding test data.
    """
    # Validated here, before it ever reaches SQL — never interpolated
    # into any message.
    policy_app_password = os.environ.get("POLICY_APP_PASSWORD", "")
    if not policy_app_password:
        raise ValueError("POLICY_APP_PASSWORD must be set to a non-empty value")

    pg_connection.execute(
        "SELECT set_config('app.policy_app_bootstrap_password', %s, false)",
        (policy_app_password,),
    )
    apply_migrations(REAL_MIGRATIONS_DIR, pg_connection)
    return pg_connection


@pytest.fixture
def policy_app_connection(policy_app_ready: psycopg.Connection) -> Iterator[psycopg.Connection]:
    """A connection to the dedicated test database authenticated as
    policy_app, in the default (non-autocommit) mode — matching how a
    real backend would wrap set_config(..., true) and a query in one
    explicit transaction.
    """
    conn = _connect(
        TEST_DATABASE_NAME,
        user="policy_app",
        password=os.environ["POLICY_APP_PASSWORD"],
    )
    try:
        yield conn
    finally:
        conn.close()
