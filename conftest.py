"""Pytest fixtures for the KilnCoffee Flask demo."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as kiln_app  # pylint: disable=wrong-import-position


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A Flask test client backed by a fresh, isolated SQLite DB and log file
    per test — never touches the real kiln.db/requests.log on disk."""
    db_path = tmp_path / "kiln_test.db"
    log_path = tmp_path / "requests_test.log"

    monkeypatch.setattr(kiln_app, "DB_PATH", str(db_path))
    monkeypatch.setattr(kiln_app, "LOG_PATH", str(log_path))

    kiln_app.app.config["TESTING"] = True
    kiln_app.app.config["SECURE_MODE"] = False
    kiln_app.init_db()

    with kiln_app.app.test_client() as test_client:
        yield test_client


def login(test_client, username, password="coffee123"):
    """Log a test client in as the requested demo user."""
    return test_client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )
