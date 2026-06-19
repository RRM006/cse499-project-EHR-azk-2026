"""Offline tests for the STT provider registry and status logic.

No network, no heavy imports: the local engines aren't installed in the core
venv, so they must report 'not_configured' and importing the registry must NOT
pull in torch / faster_whisper (lazy-import safety).
"""

import sys

import pytest

from backend.app.core.config import Settings
from backend.app.services.stt import get_provider, list_providers
from backend.app.services.stt.browser_webspeech import BrowserWebSpeechProvider
from backend.app.services.stt.groq_whisper import GroqWhisperProvider


def test_lists_all_five_providers():
    ids = [info.id for info in list_providers()]
    assert ids == [
        "browser_webspeech",
        "groq_whisper",
        "local_whisper",
        "banglaspeech2text",
        "qwen_asr",
    ]


def test_browser_provider_always_available():
    info = BrowserWebSpeechProvider(Settings()).info()
    assert info.kind == "browser"
    assert info.status == "available"
    assert info.installed and info.configured and info.ready


def test_groq_status_depends_on_key():
    no_key = GroqWhisperProvider(Settings(groq_api_key="")).info()
    assert no_key.status == "missing_api_key"
    assert no_key.installed is True and no_key.configured is False and no_key.ready is False

    with_key = GroqWhisperProvider(Settings(groq_api_key="x")).info()
    assert with_key.status == "available" and with_key.ready is True


def test_local_providers_report_consistent_health():
    # Works whether or not the optional engines are installed: status must follow
    # the `installed` flag rather than assuming a particular environment.
    infos = {i.id: i for i in list_providers()}
    for pid in ("local_whisper", "banglaspeech2text", "qwen_asr"):
        info = infos[pid]
        assert info.kind == "server"
        if not info.installed:
            assert info.status == "missing_package" and info.ready is False
        else:
            assert info.status in ("available", "missing_model")


def test_importing_registry_does_not_import_heavy_libs():
    # Lazy imports: nothing heavy should be loaded just by listing providers.
    list_providers()
    for heavy in ("torch", "faster_whisper", "banglaspeech2text", "qwen_asr", "av"):
        assert heavy not in sys.modules


def test_get_unknown_provider_raises():
    with pytest.raises(KeyError):
        get_provider("does_not_exist")
