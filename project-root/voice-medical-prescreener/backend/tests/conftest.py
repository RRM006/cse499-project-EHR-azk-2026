"""Shared test fixtures."""

import pytest

from backend.app.services.llm_client import reset_cooldowns


@pytest.fixture(autouse=True)
def _fresh_llm_cooldowns():
    """The quota-cooldown registry is process-global; a simulated 429 in one test
    must never make another test skip that provider."""
    reset_cooldowns()
    yield
    reset_cooldowns()
