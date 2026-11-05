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
from typing import TypedDict

import psycopg
import pytest
from dotenv import load_dotenv
from psycopg import sql

load_dotenv()

TEST_DATABASE_NAME = "policy_consultant_test"


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
    dbname: str, *, autocommit: bool = False, connect_timeout: int | None = None
) -> psycopg.Connection:
    params = _connection_params()
    return psycopg.connect(
        host=params["host"],
        port=params["port"],
        user=params["user"],
        password=params["password"],
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
