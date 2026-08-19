"""S44 — THREE API KEYS PER PROVIDER, tried in order before the chain moves on.

WHY THIS EXISTS, since S43 recorded the opposite decision and it is fair to ask.

ADR-0068 (g) rejected multiple keys per provider on the premise that three keys meant
three PROVIDERS, which the six-bucket registry already covered. The premise was wrong:
there are three keys **for each** of Gemini, Groq and OpenRouter — nine credentials, and
a free tier is metered per ACCOUNT, so those are nine independent daily quotas that the
architecture could not reach. ADR-0069 supersedes that rejection.

THE ORDER, which is the whole feature:

    Gemini key 1 -> key 2 -> key 3
        -> Groq key 1 -> key 2 -> key 3
            -> Cerebras (when configured)
                -> OpenRouter key 1 -> key 2 -> key 3

It is the SAME chain S42 built, not a second router: a bucket already expanded into one
attempt per model, and it now expands into one attempt per (credential, model). Nothing
in ``llm_client`` changed except the text of one log line.

The lettered tests below are the brief's scenarios A-O. Everything is MOCKED — no
network, no real credential, no quota spent (rule #4). Every fake key here is an
obvious placeholder.
"""

from __future__ import annotations

import logging

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import backend.app.services.llm_client as lc
from backend.app.core import llm_providers as lp
from backend.app.core.config import Settings
from backend.app.db.models import Base, Clinic, ModuleEvent, Visit

# Real provider wording, copied from the bodies S42 measured during the live outage.
RATE_LIMIT_429 = (
    "Error code: 429 - {'error': {'message': 'Provider returned error', 'code': 429, "
    "'metadata': {'raw': 'temporarily rate-limited upstream. Please retry shortly'}}}"
)
QUOTA_429 = (
    "Error code: 429 - {'error': {'message': 'You exceeded your current quota', "
    "'status': 'RESOURCE_EXHAUSTED', 'details': [{'quotaId': "
    "'GenerateRequestsPerDayPerProjectPerModel-FreeTier'}]}}"
)
MODEL_GONE_404 = (
    "Error code: 404 - {'error': {'message': 'The model `llama-3.3-70b-versatile` does "
    "not exist or you do not have access to it.', 'type': 'invalid_request_error', "
    "'code': 'model_not_found'}}"
)


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False},
        poolclass=StaticPool, future=True,
    )
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine, autoflush=False, future=True)()
    clinic = Clinic(name="S44 Clinic")
    db.add(clinic)
    db.flush()
    visit = Visit(clinic_id=clinic.id, uuid="s44-visit")
    db.add(visit)
    db.commit()
    yield db, visit.id
    db.close()


@pytest.fixture(autouse=True)
def _no_cooldown_bleed():
    lc.reset_cooldowns()
    yield
    lc.reset_cooldowns()


@pytest.fixture(autouse=True)
def _instant_retry(monkeypatch):
    monkeypatch.setattr(lc.time, "sleep", lambda _s: None)


def nine_keys(**over) -> Settings:
    """The layout this session was asked for: three keys each for the three providers,
    in the numbered slots, with the bare names left empty."""
    base = dict(
        gemini_api_key="", gemini_api_key_1="gem-1", gemini_api_key_2="gem-2",
        gemini_api_key_3="gem-3",
        groq_api_key="", groq_api_key_1="grq-1", groq_api_key_2="grq-2",
        groq_api_key_3="grq-3",
        openrouter_api_key="", openrouter_api_key_1="orr-1", openrouter_api_key_2="orr-2",
        openrouter_api_key_3="orr-3",
        cerebras_api_key="", mistral_api_key="",
        # one model per bucket, so a test's attempt list is exactly its key list
        gemini_flash_model="gflash", gemini_flash_lite_model="glite",
        groq_model="gq", openrouter_model="orm",
    )
    base.update(over)
    return Settings(**base)


def install_chain(monkeypatch, settings, module_code="M4"):
    """Use the REAL chain builder — the point of these tests is the chain it produces."""
    chain = lp.provider_chain_for_module(module_code, settings)
    monkeypatch.setattr(lc, "provider_chain_for_module", lambda mc, settings=None: chain)
    return chain


def record_attempts(monkeypatch, outcome):
    """Patch the one network call and record (bucket, key slot, model) per attempt.

    ⚠ The recorder deliberately stores the SLOT NUMBER, never `provider.api_key`: a test
    fixture that collected credentials would be the same mistake in miniature.
    """
    seen: list[tuple[str, int, str]] = []

    def attempt(provider, *, system, user, timeout):
        seen.append((provider.key, provider.key_index, provider.model))
        return outcome(provider)

    monkeypatch.setattr(lc, "_attempt", attempt)
    return seen


def fail_with(message):
    def raiser(_provider):
        raise RuntimeError(message)
    return raiser


def fail_until(predicate, message, success="ok"):
    """Fail every attempt for which `predicate(provider)` is true; succeed otherwise."""
    def outcome(provider):
        if predicate(provider):
            raise RuntimeError(message)
        return success
    return outcome


def call(db, visit_id, module_code="M4"):
    return lc.call_module(db, visit_id=visit_id, module_code=module_code, system="s", user="u")


# ====================================================================================
#  The order itself
# ====================================================================================


def test_the_chain_is_key_major_per_bucket_in_the_documented_order():
    """The picture from the brief, asserted as a list."""
    chain = lp.provider_chain_for_module("M4", nine_keys())
    assert [(p.key, p.key_index) for p in chain] == [
        ("gemini_flash", 1), ("gemini_flash", 2), ("gemini_flash", 3),
        ("groq", 1), ("groq", 2), ("groq", 3),
        ("openrouter", 1), ("openrouter", 2), ("openrouter", 3),
    ]


def test_every_model_of_one_key_is_tried_before_the_next_key():
    """Key-major with several models: key 1's whole model list, then key 2's."""
    s = nine_keys(openrouter_model="m-a,m-b")
    attempts = [(p.key_index, p.model) for p in lp.provider_variants(lp.OPENROUTER, s)]
    assert attempts == [(1, "m-a"), (1, "m-b"), (2, "m-a"), (2, "m-b"), (3, "m-a"), (3, "m-b")]


def test_the_existing_provider_order_is_unchanged():
    """S44 multiplies the attempts inside each bucket; it must not reorder the buckets."""
    order = []
    for p in lp.provider_chain_for_module("M3", nine_keys()):
        if p.key not in order:
            order.append(p.key)
    assert order == ["gemini_flash_lite", "groq", "openrouter"]
    assert lp.FALLBACK_ORDER == [lp.GROQ, lp.CEREBRAS, lp.MISTRAL, lp.OPENROUTER]


def test_one_key_configured_behaves_exactly_as_before():
    """The regression that matters most: an existing .env is untouched by this change."""
    s = nine_keys(gemini_api_key_1="", gemini_api_key_2="", gemini_api_key_3="",
                  gemini_api_key="only-one")
    gem = [p for p in lp.provider_chain_for_module("M4", s) if p.key == "gemini_flash"]
    assert [(p.key_index, p.model) for p in gem] == [(1, "gflash")]


# ====================================================================================
#  A-D — Gemini
# ====================================================================================


def test_A_first_key_succeeds_and_the_others_are_never_called(db_session, monkeypatch):
    db, visit_id = db_session
    install_chain(monkeypatch, nine_keys())
    seen = record_attempts(monkeypatch, lambda _p: "answer")
    assert call(db, visit_id) == "answer"
    assert seen == [("gemini_flash", 1, "gflash")]


def test_B_first_gemini_key_429s_and_the_second_is_attempted(db_session, monkeypatch):
    db, visit_id = db_session
    install_chain(monkeypatch, nine_keys())
    seen = record_attempts(monkeypatch, fail_until(
        lambda p: p.key == "gemini_flash" and p.key_index == 1, RATE_LIMIT_429))
    assert call(db, visit_id) == "ok"
    assert seen == [("gemini_flash", 1, "gflash"), ("gemini_flash", 2, "gflash")]


def test_C_two_gemini_keys_429_and_the_third_is_attempted(db_session, monkeypatch):
    db, visit_id = db_session
    install_chain(monkeypatch, nine_keys())
    seen = record_attempts(monkeypatch, fail_until(
        lambda p: p.key == "gemini_flash" and p.key_index in (1, 2), QUOTA_429))
    assert call(db, visit_id) == "ok"
    assert [k for _b, k, _m in seen] == [1, 2, 3]
    assert {b for b, _k, _m in seen} == {"gemini_flash"}


def test_D_all_three_gemini_keys_fail_and_the_next_provider_takes_over(db_session, monkeypatch):
    db, visit_id = db_session
    install_chain(monkeypatch, nine_keys())
    seen = record_attempts(monkeypatch, fail_until(
        lambda p: p.key == "gemini_flash", QUOTA_429))
    assert call(db, visit_id) == "ok"
    assert seen == [
        ("gemini_flash", 1, "gflash"), ("gemini_flash", 2, "gflash"),
        ("gemini_flash", 3, "gflash"), ("groq", 1, "gq"),
    ]


# ====================================================================================
#  E-G — Groq
# ====================================================================================


def test_E_groq_key_1_429s_and_key_2_is_attempted(db_session, monkeypatch):
    db, visit_id = db_session
    install_chain(monkeypatch, nine_keys())
    seen = record_attempts(monkeypatch, fail_until(
        lambda p: p.key == "gemini_flash" or (p.key == "groq" and p.key_index == 1),
        RATE_LIMIT_429))
    assert call(db, visit_id) == "ok"
    assert seen[-2:] == [("groq", 1, "gq"), ("groq", 2, "gq")]


def test_F_groq_keys_1_and_2_429_and_key_3_is_attempted(db_session, monkeypatch):
    db, visit_id = db_session
    install_chain(monkeypatch, nine_keys())
    seen = record_attempts(monkeypatch, fail_until(
        lambda p: p.key == "gemini_flash" or (p.key == "groq" and p.key_index in (1, 2)),
        RATE_LIMIT_429))
    assert call(db, visit_id) == "ok"
    assert [k for b, k, _m in seen if b == "groq"] == [1, 2, 3]


def test_G_all_groq_keys_fail_and_openrouter_takes_over(db_session, monkeypatch):
    db, visit_id = db_session
    install_chain(monkeypatch, nine_keys())
    seen = record_attempts(monkeypatch, fail_until(
        lambda p: p.key in ("gemini_flash", "groq"), QUOTA_429))
    assert call(db, visit_id) == "ok"
    assert seen[-1] == ("openrouter", 1, "orm")
    assert len(seen) == 7      # 3 gemini + 3 groq + 1 openrouter


# ====================================================================================
#  H-J — OpenRouter, the universal fallback
# ====================================================================================


def test_H_openrouter_key_1_429s_and_key_2_is_attempted(db_session, monkeypatch):
    db, visit_id = db_session
    install_chain(monkeypatch, nine_keys())
    seen = record_attempts(monkeypatch, fail_until(
        lambda p: p.key in ("gemini_flash", "groq") or (p.key == "openrouter" and p.key_index == 1),
        RATE_LIMIT_429))
    assert call(db, visit_id) == "ok"
    assert seen[-2:] == [("openrouter", 1, "orm"), ("openrouter", 2, "orm")]


def test_I_openrouter_keys_1_and_2_429_and_key_3_is_attempted(db_session, monkeypatch):
    db, visit_id = db_session
    install_chain(monkeypatch, nine_keys())
    seen = record_attempts(monkeypatch, fail_until(
        lambda p: p.key in ("gemini_flash", "groq")
        or (p.key == "openrouter" and p.key_index in (1, 2)), RATE_LIMIT_429))
    assert call(db, visit_id) == "ok"
    assert [k for b, k, _m in seen if b == "openrouter"] == [1, 2, 3]


def test_J_all_nine_keys_fail_and_the_chain_ends_in_a_controlled_error(db_session, monkeypatch):
    """There is no provider after OpenRouter — 'the next configured provider' is the
    honest 502, and it must be an error rather than a crash or a hang."""
    db, visit_id = db_session
    install_chain(monkeypatch, nine_keys())
    seen = record_attempts(monkeypatch, fail_with(QUOTA_429))
    with pytest.raises(lc.LLMCallError) as caught:
        call(db, visit_id)
    assert [(b, k) for b, k, _m in seen][:9] == [
        ("gemini_flash", 1), ("gemini_flash", 2), ("gemini_flash", 3),
        ("groq", 1), ("groq", 2), ("groq", 3),
        ("openrouter", 1), ("openrouter", 2), ("openrouter", 3),
    ]
    assert caught.value.safe_detail == lc.LLM_UNAVAILABLE_DETAIL


def test_J2_cerebras_still_sits_between_groq_and_openrouter_when_configured(db_session, monkeypatch):
    """The optional bucket keeps its place in FALLBACK_ORDER — S44 did not reorder it."""
    db, visit_id = db_session
    install_chain(monkeypatch, nine_keys(cerebras_api_key="cbs-1", cerebras_model="cbm"))
    seen = record_attempts(monkeypatch, fail_until(
        lambda p: p.key in ("gemini_flash", "groq"), QUOTA_429))
    assert call(db, visit_id) == "ok"
    assert seen[-1] == ("cerebras", 1, "cbm")


# ====================================================================================
#  K-O — the properties around the order
# ====================================================================================


def test_K_a_successful_fallback_returns_exactly_one_response(db_session, monkeypatch):
    """One answer, one 'fallback' event for the attempt that worked, and nothing
    attempted after it."""
    db, visit_id = db_session
    install_chain(monkeypatch, nine_keys())
    seen = record_attempts(monkeypatch, fail_until(
        lambda p: p.key == "gemini_flash", QUOTA_429, success="the answer"))
    assert call(db, visit_id) == "the answer"
    assert seen[-1] == ("groq", 1, "gq")
    ok_events = [e for e in db.query(ModuleEvent).all() if e.status in ("ok", "fallback")]
    assert len(ok_events) == 1
    assert ok_events[0].status == "fallback"
    # ⚠ module_events still records the BUCKET only — no credential slot is persisted.
    assert ok_events[0].provider == "groq"


def test_L_the_patients_utterance_is_never_submitted_more_than_once(db_session, monkeypatch):
    """Rule #1 across the whole 9-key chain. call_module is a PURE model call: it may be
    attempted nine times and it must never be a write path. Asserted structurally,
    because 'it happens not to write today' is not a guarantee."""
    db, visit_id = db_session
    install_chain(monkeypatch, nine_keys())
    record_attempts(monkeypatch, fail_until(lambda p: p.key != "openrouter", QUOTA_429))
    before = db.query(ModuleEvent).count()
    call(db, visit_id)
    # The only rows a retried chain may add are observability events, never content.
    import inspect
    source = inspect.getsource(lc)
    for writer in ("Utterance(", "raw_text", "add_utterance"):
        assert writer not in source, f"llm_client can write {writer} — a retry would duplicate it"
    assert db.query(ModuleEvent).count() > before


def test_M_a_dead_nine_key_chain_leaks_no_upstream_detail(db_session, monkeypatch):
    db, visit_id = db_session
    install_chain(monkeypatch, nine_keys())
    record_attempts(monkeypatch, fail_with(RATE_LIMIT_429))
    with pytest.raises(lc.LLMCallError) as caught:
        call(db, visit_id)
    safe = caught.value.safe_detail
    for leak in ("429", "rate-limited", "upstream", "http", "quota", "gemini", "groq",
                 "openrouter", "gflash"):
        assert leak.lower() not in safe.lower()
    assert "try again" in safe.lower()


def test_N_a_missing_middle_key_does_not_stop_the_others(db_session, monkeypatch):
    """Sparse configuration is legal: key 1 and key 3 set, key 2 blank. Blanks are
    dropped, so those two become slots 1 and 2 and BOTH are used."""
    db, visit_id = db_session
    s = nine_keys(gemini_api_key_2="")
    assert len(lp.provider_api_keys(lp.GEMINI_FLASH, s)) == 2
    install_chain(monkeypatch, s)
    seen = record_attempts(monkeypatch, fail_until(
        lambda p: p.key == "gemini_flash" and p.key_index == 1, QUOTA_429))
    assert call(db, visit_id) == "ok"
    assert seen == [("gemini_flash", 1, "gflash"), ("gemini_flash", 2, "gflash")]


def test_N2_the_same_key_pasted_twice_is_one_quota_not_two():
    """Trying an identical credential again would spend the patient's time proving the
    same 429 twice, and would make the slot report overstate the redundancy available."""
    s = nine_keys(gemini_api_key_1="same", gemini_api_key_2="same", gemini_api_key_3="other")
    assert lp.provider_api_keys(lp.GEMINI_FLASH, s) == ["same", "other"]


def test_N3_whitespace_around_a_pasted_key_is_stripped():
    s = nine_keys(gemini_api_key_1="  padded  ", gemini_api_key_2="", gemini_api_key_3="")
    assert lp.provider_api_keys(lp.GEMINI_FLASH, s) == ["padded"]


def test_O_the_checker_sees_all_nine_configured_keys():
    from backend.scripts import check_api_keys as chk

    s = nine_keys()
    assert len(lp.provider_api_keys(lp.GEMINI_FLASH, s)) == 3
    assert len(lp.provider_api_keys(lp.GROQ, s)) == 3
    assert len(lp.provider_api_keys(lp.OPENROUTER, s)) == 3
    # Flash-Lite shares the Gemini credentials — one account, two per-model quotas.
    assert lp.provider_api_keys(lp.GEMINI_FLASH_LITE, s) == lp.provider_api_keys(lp.GEMINI_FLASH, s)
    # The checker knows the .env names for every slot it reports.
    for bucket in (lp.GEMINI_FLASH, lp.GROQ, lp.OPENROUTER):
        assert len(lp.KEY_ENV_NAMES[bucket]) == 4
    assert chk.report_slots(lp.GROQ, s) == 3


def test_O2_the_checker_never_calls_a_provider_dead_while_one_key_works(monkeypatch, capsys):
    """'Do not falsely report a provider as unavailable merely because one of its keys
    is missing if another valid key is configured.'"""
    from backend.scripts import check_api_keys as chk

    s = nine_keys(gemini_api_key_2="", gemini_api_key_3="")
    monkeypatch.setattr(chk, "get_settings", lambda: s)
    monkeypatch.setattr(
        chk, "_probe",
        lambda provider: (provider.key_index == 1, "authenticated"
                          if provider.key_index == 1 else "429"),
    )
    assert chk.main() == 0
    out = capsys.readouterr().out
    assert "FAILED" not in out
    assert "key 1 configured" in out


def test_O3_the_checker_reports_slots_without_ever_printing_a_key(capsys):
    from backend.scripts import check_api_keys as chk

    s = nine_keys()
    for bucket in (lp.GEMINI_FLASH, lp.GROQ, lp.OPENROUTER):
        chk.report_slots(bucket, s)
    out = capsys.readouterr().out
    for secret in ("gem-1", "gem-2", "gem-3", "grq-1", "grq-2", "grq-3",
                   "orr-1", "orr-2", "orr-3"):
        assert secret not in out
    assert out.count("key 1 configured") == 3
    assert out.count("key 2 configured") == 3
    assert out.count("key 3 configured") == 3


def test_the_env_names_the_checker_prints_all_exist_as_settings():
    """A report that names a variable nothing reads sends the operator to edit the
    wrong line — the exact failure S43 fixed in this same script."""
    fields = set(Settings.model_fields)
    for bucket, names in lp.KEY_ENV_NAMES.items():
        for name in names:
            assert name.lower() in fields, f"{name} ({bucket}) is not a Settings field"


# ====================================================================================
#  404 / decommissioned model, and the credential-safety properties
# ====================================================================================


def test_a_decommissioned_model_falls_through_every_key_of_that_bucket(db_session, monkeypatch):
    """A 404 is a property of the MODEL, so every key of that bucket meets it — and none
    of them is retried, because the existing policy never retries a permanent failure."""
    db, visit_id = db_session
    install_chain(monkeypatch, nine_keys())
    seen = record_attempts(monkeypatch, fail_until(
        lambda p: p.key == "gemini_flash", MODEL_GONE_404))
    assert call(db, visit_id) == "ok"
    assert [(b, k) for b, k, _m in seen] == [
        ("gemini_flash", 1), ("gemini_flash", 2), ("gemini_flash", 3), ("groq", 1)]
    assert not lc.is_transient(RuntimeError(MODEL_GONE_404))


def test_a_429_on_one_key_does_not_cool_down_another_key(db_session, monkeypatch):
    """The crux of the whole change. A free quota belongs to an ACCOUNT: key 1 being
    spent says nothing about key 2, so the cooldown must distinguish them or two good
    quotas are put to sleep on the evidence of a third."""
    db, visit_id = db_session
    chain = install_chain(monkeypatch, nine_keys())
    record_attempts(monkeypatch, fail_until(
        lambda p: p.key == "gemini_flash" and p.key_index == 1, QUOTA_429))
    call(db, visit_id)

    gem = [p for p in chain if p.key == "gemini_flash"]
    assert lc._on_cooldown(gem[0].cooldown_key), "key 1 hit a daily quota and should cool down"
    assert not lc._on_cooldown(gem[1].cooldown_key), "key 2 was never even called"
    assert not lc._on_cooldown(gem[2].cooldown_key)
    # …and the cooldown is time-based, so nothing is permanently disabled.
    assert lc.DAILY_QUOTA_COOLDOWN_S > 0 and lc.RATE_LIMIT_COOLDOWN_S > 0


def test_a_cooled_key_is_skipped_but_its_siblings_are_not(db_session, monkeypatch):
    db, visit_id = db_session
    install_chain(monkeypatch, nine_keys())
    outcome = fail_until(lambda p: p.key == "gemini_flash" and p.key_index == 1, QUOTA_429)
    record_attempts(monkeypatch, outcome)
    call(db, visit_id)                      # key 1 goes on cooldown
    seen2 = record_attempts(monkeypatch, outcome)
    assert call(db, visit_id) == "ok"
    assert seen2 == [("gemini_flash", 2, "gflash")], "the spent key should be skipped, not the rest"


def test_no_key_value_reaches_a_log_line_a_module_event_or_the_error(db_session, monkeypatch, caplog):
    db, visit_id = db_session
    secret = "sk-live-S44-DO-NOT-LOG-THIS-0123456789"
    s = nine_keys(gemini_api_key_1=secret)
    install_chain(monkeypatch, s)
    record_attempts(monkeypatch, fail_with(QUOTA_429))

    with caplog.at_level(logging.DEBUG):
        with pytest.raises(lc.LLMCallError) as caught:
            call(db, visit_id)

    assert secret not in caplog.text
    assert secret not in str(caught.value)
    assert secret not in caught.value.safe_detail
    for ev in db.query(ModuleEvent).all():
        assert secret not in (ev.error or "")
        assert secret not in (ev.provider or "")
    # The diagnostics that ARE wanted survived — including WHICH SLOT failed.
    assert "gemini_flash key 1" in caplog.text


def test_the_provider_label_is_safe_by_construction():
    p = lp.ProviderConfig("groq", "sk-secret-value", "http://x", "m", 2)
    assert p.label == "groq key 2 [m]"
    assert "secret" not in p.label
    assert "sk-" not in p.cooldown_key


def test_module_events_still_record_the_bucket_only():
    """The stored shape is unchanged: no credential slot reaches the database."""
    import inspect
    source = inspect.getsource(lc.call_module)
    assert "provider=provider.key" in source
    assert "key_index" not in source
