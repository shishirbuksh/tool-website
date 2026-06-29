"""Pytest fixtures: test client, settings, and service instances."""

import pytest

from app.core.config import Settings


@pytest.fixture
def settings():
    return Settings()
