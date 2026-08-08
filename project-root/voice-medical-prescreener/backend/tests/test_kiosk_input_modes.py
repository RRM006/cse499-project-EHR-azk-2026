"""S2 of ADR-0048 — the kiosk offers BOTH voice and typing, in both docks.

⚠ Scope, stated honestly (the human's S28 decision (2)): these are **static-source
assertions** over the served files, the same pattern as `test_routes_static.py`. They
prove the controls and their wiring still EXIST — they cannot prove browser behaviour.
Microphone, TTS, silence detection, the countdown and barge-in are provable ONLY by the
12-point live Chrome run in `agent_docs/faculty_future_features.md` §K. Do not read a
green suite here as "the voice UX works".
"""

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)

VOICE_DOCK_IDS = ("mode-voice-btn", "mode-type-btn")
RESUME_DOCK_IDS = ("resume-mode-voice-btn", "resume-mode-type-btn")


def kiosk_html() -> str:
    resp = client.get("/kiosk.html")
    assert resp.status_code == 200
    return resp.text


def kiosk_js() -> str:
    resp = client.get("/kiosk.js")
    assert resp.status_code == 200
    return resp.text


def test_both_docks_offer_a_voice_and_a_typing_control():
    """The conversation screen AND the KIOSK-7 resume dock each get the choice."""
    html = kiosk_html()
    for element_id in VOICE_DOCK_IDS + RESUME_DOCK_IDS:
        assert f'id="{element_id}"' in html, f"missing input-mode control: {element_id}"


def test_the_active_mode_is_announced_to_the_patient_and_to_assistive_tech():
    html = kiosk_html()
    # Voice is pressed by default in the markup; the switch is a labelled group.
    assert html.count('aria-pressed="true"') >= 2   # one per dock
    assert html.count('aria-pressed="false"') >= 2
    assert 'aria-label="Answer using voice or typing"' in html


def test_mode_buttons_are_bilingual():
    """P1-2: JS/markup text must follow the EN/BN toggle."""
    html = kiosk_html()
    assert 'data-en="🎤 Speak"' in html and 'data-bn="🎤 বলুন"' in html
    assert 'data-en="⌨ Type"' in html and 'data-bn="⌨ টাইপ করুন"' in html


def test_typing_is_no_longer_hidden_behind_a_microphone_failure_link():
    """S2 promotes typing to a first-class choice — the old reveal link is gone."""
    html = kiosk_html()
    assert "Microphone issue? Type instead" not in html
    assert "document.getElementById('fallback-row').style.display='flex'" not in html


def test_both_typed_inputs_and_their_send_handlers_survive():
    html = kiosk_html()
    for element_id in ("fallback-input", "resume-fallback-input"):
        assert f'id="{element_id}"' in html
    assert "sendTypedFallback()" in html
    assert "sendResumeTyped()" in html


def test_the_mode_switch_is_wired_to_setinputmode():
    html = kiosk_html()
    assert html.count("setInputMode('voice')") >= 2   # one button per dock
    assert html.count("setInputMode('type')") >= 2


def test_voice_is_the_default_mode():
    """ADR-0048: voice is the PRIMARY interaction — every reset returns to it."""
    js = kiosk_js()
    assert "inputMode: 'voice'" in js          # initial state
    assert "setInputMode('voice', { focus: false })" in js  # load + post-logout reset


def test_switching_to_typing_discards_the_unsubmitted_voice_buffer():
    """Rule #1 / ADR-0048: never merge STT text with typed edits into one utterance."""
    js = kiosk_js()
    assert "if (typing && listening) stopListening(false);" in js


def test_a_dead_microphone_switches_the_patient_to_typing():
    """The patient must never be stranded — mic errors fall through to typing."""
    js = kiosk_js()
    assert js.count("setInputMode('type')") >= 2   # onerror + unsupported browser


def test_one_mode_switch_updates_both_docks():
    """The patient picks once; the resume dock inherits it."""
    js = kiosk_js()
    assert "Object.values(DOCKS).forEach" in js
    assert "conversation:" in js and "resume:" in js


def test_typing_and_speaking_still_share_one_pipeline():
    """ADR-0048: no second question/answer path — only `source` differs."""
    js = kiosk_js()
    assert "submitPatientTurn(text, 'manual')" in js
    assert "submitPatientTurn(text, 'mic')" in js
    assert "submitResumeAnswer(text, 'manual')" in js
    assert "submitResumeAnswer(text, 'mic')" in js
