"""Offline unit checks for the correction service.

These never touch the network: they cover the guards around the LLM call
(empty input, provider selection, missing key). The actual live Gemini call is
verified manually via the module's __main__.
"""

import pytest

from backend.app.core.config import Settings
from backend.app.services.correction.openai_compatible import (
    OpenAICompatibleCorrector,
    build_corrector,
)


def test_empty_input_is_returned_unchanged_without_api_call():
    # A dummy key is fine — constructing the client makes no network call, and
    # whitespace-only input short-circuits before any request is sent.
    c = OpenAICompatibleCorrector(
        api_key="dummy", base_url="http://localhost", model="m", provider="gemini"
    )
    assert c.correct("   ") == "   "
    assert c.correct("") == ""


def test_build_corrector_selects_gemini():
    s = Settings(
        correction_provider="gemini",
        gemini_api_key="dummy-key",
        correction_model="gemini-flash-latest",
    )
    corrector = build_corrector(s)
    assert corrector.provider == "gemini"
    assert corrector.model == "gemini-flash-latest"


def test_build_corrector_requires_a_key():
    s = Settings(correction_provider="gemini", gemini_api_key="")
    with pytest.raises(RuntimeError):
        build_corrector(s)


def test_build_corrector_rejects_unknown_provider():
    s = Settings(correction_provider="not-a-provider")
    with pytest.raises(ValueError):
        build_corrector(s)
