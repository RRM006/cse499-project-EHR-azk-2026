"""S43 — the provider CONFIGURATION surface, and the one provider leak S42 missed.

S42 hardened the *runtime* chain and ``test_provider_failure_s42.py`` pins that work:
a healthy primary, a 429/404/401/5xx falling through, a dead chain answering a
patient-safe 502, the bounded retry, the call deadline, and no key in a log record.
None of that is repeated here. What is pinned below is the layer underneath it — how a
bucket gets configured in the first place — plus the two properties S42 stated but did
not test.

THE CONFIGURATION BUG, stated plainly because it is the demo-relevant one:

    OPENROUTER_MODEL=

One blank line. The key is present and valid, so nothing looks wrong. But
``split_models("")`` is ``[]``, ``provider_variants`` therefore returns no attempts, and
``provider_chain_for_module`` skips the bucket entirely — deleting ADR-0026's UNIVERSAL
FALLBACK with no error, no warning and no trace. ``check_api_keys`` made it worse by
reporting that bucket as "not set", i.e. blaming a key that was fine. A configuration
mistake that reports itself as an unrelated fact is the kind that survives a checklist.

THE LEAK: ``POST /api/correct`` (Module 2, reached through the ``Corrector`` seam rather
than ``call_module``) still answered ``detail=f"Correction failed: {exc}"`` — the same
raw upstream body S42 removed from six other routes, on a route anyone can reach.

Synthetic data only; no network, no real .env, no real DB (rule #4).
"""

from __future__ import annotations

import pathlib
import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core import llm_providers as lp
from backend.app.core.config import Settings
from backend.app.db.database import Base, get_db
from backend.app.main import app
from backend.app.services.llm_client import LLM_UNAVAILABLE_DETAIL

BACKEND = pathlib.Path(__file__).resolve().parents[1]
PROJECT = BACKEND.parent
ENV_EXAMPLE = BACKEND / ".env.example"

# A realistic upstream body, in the shape S42 measured during the real outage. Every
# term in LEAKY_TERMS is something a patient must never be shown.
UPSTREAM_BODY = (
    "Error code: 429 - {'error': {'message': 'google/gemma-4-31b-it:free is temporarily "
    "rate-limited upstream. Please retry shortly, or add your own key to accumulate your "
    "rate limits: https://openrouter.ai/settings/integrations', "
    "'metadata': {'provider_name': 'Google AI Studio'}}}"
)
LEAKY_TERMS = ("openrouter", "gemma", "provider_name", "Google AI Studio", "http", "429")


def blank_keys(**over) -> Settings:
    """A Settings with every provider credential explicitly empty, then the overrides.

    Explicit blanks matter: without them the developer's real backend/.env would decide
    the result of these tests, which is exactly the kind of hidden dependency this file
    is about.
    """
    base = dict(
        gemini_api_key="", groq_api_key="", openrouter_api_key="",
        cerebras_api_key="", mistral_api_key="",
    )
    base.update(over)
    return Settings(**base)


# --- 1. a key with no model is a MISCONFIGURATION, not an unconfigured bucket --------


def test_a_key_with_a_blank_model_is_reported_as_misconfigured():
    s = blank_keys(groq_api_key="dummy", groq_model="")
    assert lp.GROQ in lp.misconfigured_buckets(s)


def test_a_bucket_with_neither_key_nor_model_is_NOT_a_misconfiguration():
    """The normal, intended state of every optional bucket. Reporting it would train
    the operator to ignore the report."""
    s = blank_keys(cerebras_api_key="", cerebras_model="")
    assert lp.CEREBRAS not in lp.misconfigured_buckets(s)


def test_a_fully_configured_bucket_is_not_reported():
    s = blank_keys(openrouter_api_key="dummy", openrouter_model="a:free,b:free")
    assert lp.OPENROUTER not in lp.misconfigured_buckets(s)


def test_whitespace_only_is_blank_a_stray_space_must_not_look_configured():
    s = blank_keys(openrouter_api_key="dummy", openrouter_model="   ,  ")
    assert lp.OPENROUTER in lp.misconfigured_buckets(s)


# --- 2. WHY it matters: the bucket really does vanish from the chain -----------------


def test_the_universal_fallback_can_be_deleted_by_one_blank_line():
    """The failure this whole check exists for, made explicit.

    Three keys configured, all valid. One blank model setting. The universal fallback
    is gone from the chain — and the ONLY thing that says so is misconfigured_buckets.
    """
    s = blank_keys(
        gemini_api_key="g", groq_api_key="k", openrouter_api_key="o", openrouter_model="",
    )
    chain = lp.provider_chain_for_module("M3", s)
    assert chain, "the chain should still have the other buckets"
    assert all(p.key != lp.OPENROUTER for p in chain), (
        "expected the blank-model bucket to be absent — if this fails the bug is fixed "
        "differently and the warning is no longer the only signal"
    )
    assert lp.misconfigured_buckets(s) == [lp.OPENROUTER]


def test_a_healthy_three_key_setup_builds_the_documented_chain():
    """The exact configuration the demo runs on: three keys, shipped model defaults."""
    s = blank_keys(gemini_api_key="g", groq_api_key="k", openrouter_api_key="o")
    assert lp.misconfigured_buckets(s) == []
    chain = lp.provider_chain_for_module("M3", s)
    keys = [p.key for p in chain]
    assert keys[0] == lp.GEMINI_FLASH_LITE      # M3's assigned bucket (ADR-0026)
    assert lp.GROQ in keys and lp.OPENROUTER in keys
    assert keys.index(lp.GROQ) < keys.index(lp.OPENROUTER), (
        "Groq must be tried before OpenRouter's shared free pool"
    )
    # Every OpenRouter model is its own attempt with its own cooldown (S42).
    or_attempts = [p for p in chain if p.key == lp.OPENROUTER]
    assert len(or_attempts) > 1
    assert len({p.cooldown_key for p in or_attempts}) == len(or_attempts)


def test_an_unconfigured_bucket_is_skipped_without_being_called_a_mistake():
    s = blank_keys(gemini_api_key="g")
    assert lp.misconfigured_buckets(s) == []
    assert all(p.key.startswith("gemini") for p in lp.provider_chain_for_module("M4", s))


# --- 3. the startup warning is wired in ---------------------------------------------


def test_the_server_warns_about_a_misconfigured_bucket_at_startup():
    """A checker the operator has to remember to run is not the same as being told."""
    main_src = (BACKEND / "app" / "main.py").read_text(encoding="utf-8")
    assert "misconfigured_buckets" in main_src
    assert "logger.warning" in main_src


# --- 4. ONE place a provider's endpoint is written down ------------------------------


@pytest.mark.parametrize(
    "bucket",
    [lp.GEMINI_FLASH, lp.GEMINI_FLASH_LITE, lp.GROQ, lp.OPENROUTER, lp.CEREBRAS, lp.MISTRAL],
)
def test_provider_credentials_agrees_with_the_chain(bucket):
    """If these two ever disagree, some caller is reaching a different endpoint than
    the pipeline is — which is precisely what a second copy of a base URL causes."""
    s = blank_keys(
        gemini_api_key="k", groq_api_key="k", openrouter_api_key="k",
        cerebras_api_key="k", mistral_api_key="k",
    )
    api_key, base_url = lp.provider_credentials(bucket, s)
    variant = lp.provider_variants(bucket, s)[0]
    assert (api_key, base_url) == (variant.api_key, variant.base_url)


def test_the_corrector_keeps_no_private_copy_of_a_provider_url():
    """S43 cleanup: the Module-2 seam used to restate Groq's and OpenRouter's base URLs.
    Published endpoints move — S41 and S42 both had to chase provider configuration —
    and a second copy is the one that gets forgotten."""
    src = (BACKEND / "app" / "services" / "correction" / "openai_compatible.py").read_text(
        encoding="utf-8"
    )
    assert "provider_credentials" in src, "the corrector must resolve through the registry"
    for url in ("https://api.groq.com", "https://openrouter.ai"):
        assert url not in src, f"{url} is written down twice again"


@pytest.mark.parametrize("provider,bucket", [("groq", lp.GROQ), ("openrouter", lp.OPENROUTER)])
def test_the_corrector_reaches_the_same_endpoint_the_chain_would(provider, bucket):
    from backend.app.services.correction import build_corrector

    s = blank_keys(correction_provider=provider, groq_api_key="k", openrouter_api_key="k")
    corrector = build_corrector(s)
    _key, expected = lp.provider_credentials(bucket, s)
    assert str(corrector._client.base_url).rstrip("/") == expected.rstrip("/")


def test_the_corrector_still_refuses_an_unknown_provider_and_a_missing_key():
    """Configuration errors stay loud — they are not swallowed by the new lookup."""
    from backend.app.services.correction import build_corrector

    with pytest.raises(ValueError):
        build_corrector(blank_keys(correction_provider="not-a-provider"))
    with pytest.raises(RuntimeError):
        build_corrector(blank_keys(correction_provider="groq", groq_api_key=""))


# --- 5. the leak S42 missed: POST /api/correct --------------------------------------


class _ExplodingCorrector:
    provider = "openrouter"
    model = "google/gemma-4-31b-it:free"

    def correct(self, raw_text: str) -> str:
        raise RuntimeError(UPSTREAM_BODY)


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False},
        poolclass=StaticPool, future=True,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, future=True)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)          # no `with` -> the real DB is never migrated
    app.dependency_overrides.clear()


def save_raw(client, text: str) -> int:
    resp = client.post(
        "/api/transcripts",
        json={"raw_text": text, "stt_provider": "browser_webspeech", "source": "mic"},
    )
    assert resp.status_code == 200
    return resp.json()["id"]


def test_correct_never_shows_the_caller_the_upstream_provider_body(client, monkeypatch, caplog):
    monkeypatch.setattr(
        "backend.app.api.routes_transcripts.build_corrector",
        lambda *a, **k: _ExplodingCorrector(),
    )
    uid = save_raw(client, "amar jor")

    with caplog.at_level("WARNING"):
        resp = client.post("/api/correct", json={"utterance_id": uid})

    assert resp.status_code == 502
    detail = resp.json()["detail"]
    assert detail == LLM_UNAVAILABLE_DETAIL
    for term in LEAKY_TERMS:
        assert term.lower() not in detail.lower(), f"{term!r} reached the caller"
    assert resp.headers.get("Retry-After")
    # Not lost — just moved to where a developer is.
    assert any("Correction failed" in r.getMessage() for r in caplog.records)


def test_correct_leaves_the_raw_text_untouched_when_the_provider_fails(client, monkeypatch):
    """Rule #1 through a failure path: a 502 must not have edited anything."""
    monkeypatch.setattr(
        "backend.app.api.routes_transcripts.build_corrector",
        lambda *a, **k: _ExplodingCorrector(),
    )
    uid = save_raw(client, "amar onek jor")
    assert client.post("/api/correct", json={"utterance_id": uid}).status_code == 502
    after = client.get(f"/api/transcripts/{uid}").json()
    assert after["raw_text"] == "amar onek jor"
    assert not after.get("corrected_text")


def test_a_missing_corrector_config_is_still_reported_not_hidden(client, monkeypatch):
    """'Do not silently hide configuration errors' — a 500 that names the .env problem
    is correct here, and it carries no provider body and no credential."""

    def _boom(*a, **k):
        raise RuntimeError("No API key configured for provider 'gemini'. "
                           "Set the matching key in backend/.env.")

    monkeypatch.setattr("backend.app.api.routes_transcripts.build_corrector", _boom)
    uid = save_raw(client, "jor")
    resp = client.post("/api/correct", json={"utterance_id": uid})
    assert resp.status_code == 500
    assert "backend/.env" in resp.json()["detail"]


def test_no_route_answers_with_a_provider_exception_from_the_corrector_seam():
    """Companion to S42's test_7b, which only inspects files that mention LLMCallError
    and therefore could never have caught routes_transcripts.py."""
    src = (BACKEND / "app" / "api" / "routes_transcripts.py").read_text(encoding="utf-8")
    assert "provider_unavailable" in src
    assert "Correction failed: {exc}" not in src


# --- 6. the patient's utterance is never submitted twice (rule #1) -------------------


def kiosk_js() -> str:
    return (PROJECT / "frontend" / "kiosk.js").read_text(encoding="utf-8")


def async_fn_body(name: str, source: str) -> str:
    marker = f"async function {name}("
    assert marker in source, f"{name}() is gone from the kiosk"
    return source.split(marker)[1].split("\n}")[0]


@pytest.mark.parametrize("unit", ["startOpeningLoop", "buildSummary"])
def test_a_retry_unit_never_re_posts_the_patients_words(unit):
    """The retry button resumes from the step that FAILED. If a retry unit could post
    an utterance, one sentence spoken once would appear twice in a verbatim record."""
    body = async_fn_body(unit, kiosk_js())
    assert "/utterances" not in body, (
        f"{unit} can write an utterance — retrying it would duplicate the patient's words"
    )


def test_the_retry_button_is_handed_only_those_units():
    handed = set(re.findall(r"showAiRetry\(\(\) => (\w+)\(", kiosk_js()))
    assert handed == {"startOpeningLoop", "buildSummary"}, (
        f"a new retry unit appeared ({handed}) — prove it cannot re-post an utterance"
    )


# --- 7. .env.example: complete, placeholder-only, and the only one ------------------


PROVIDER_SETTING_RE = re.compile(
    r"^(gemini|groq|openrouter|cerebras|mistral)\w*(_api_key|_model|_base_url)$"
)


def test_env_example_documents_every_provider_setting():
    """A setting that exists in code but nowhere in .env.example is a knob nobody can
    find — including the ones that silently delete a fallback bucket."""
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    missing = [
        name.upper() for name in Settings.model_fields
        if PROVIDER_SETTING_RE.match(name) and name.upper() not in text
    ]
    assert not missing, f"undocumented in .env.example: {missing}"


def test_env_example_carries_no_real_credential():
    """Placeholders only. Every provider key line must be empty or commented out."""
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#") or "=" not in stripped:
            continue
        name, _, value = stripped.partition("=")
        if name.strip().upper().endswith("API_KEY"):
            assert value.strip() == "", f".env.example line {i} carries a value for {name}"
    assert not re.search(r"(sk-|gsk_|AIza|csk-|or-v1-)[A-Za-z0-9_-]{8,}", text)


def test_there_is_exactly_one_env_example():
    """S43 removed backend/.envnew.example: a second, partial copy that told the reader
    to make it their .env, and would have produced one with no DATABASE_URL, no OTP
    channel, no TTS provider and no voice-loop settings."""
    examples = sorted(p.name for p in BACKEND.glob(".env*example"))
    assert examples == [".env.example"], f"contradictory env templates: {examples}"


def test_env_is_ignored_by_git():
    lines = [ln.strip() for ln in (PROJECT / ".gitignore").read_text(encoding="utf-8").splitlines()]
    assert "*.env" in lines
    assert "!*.env.example" in lines
