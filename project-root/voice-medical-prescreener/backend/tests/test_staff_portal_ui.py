"""S37 (ADR-0059) — static-source assertions over the two STAFF portals.

There is still no JS test runner in this project (the S28 decision: frontend tests
are static-source assertions only, no vitest/jsdom), so these read the SERVED files
and assert properties of the shipped source — the same method as the whole
``test_kiosk_*`` family.

What is worth pinning here, and why:

  * **The reduced-motion guard.** motion.css claims a user who asks their OS for less
    motion gets a completely static portal. That is an accessibility promise, and a
    single ``animation:`` added outside the guard silently breaks it while everything
    still looks right to the author. The check parses the file and proves containment.
  * **Role separation.** The medic and doctor portals share a stylesheet, a queue
    renderer and a case view, which is exactly the situation in which one portal
    quietly grows the other's workflow. These assert the two never call each other's
    endpoints.
  * **Rule #1 in the timeline.** The doctor's history panel must never render a raw
    or corrected transcript — prior words are read by opening the prior visit.
"""

import re

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def _served(path: str) -> str:
    resp = client.get(path)
    assert resp.status_code == 200, f"{path} -> {resp.status_code}"
    return resp.text


MEDIC = _served("/medic/")
DOCTOR = _served("/doctor/")
MOTION = _served("/shared/motion.css")
STAFF_JS = _served("/shared/staff.js")


def _strip_comments(css: str) -> str:
    """Blank out /* ... */ while preserving offsets, so a phrase quoted in a comment
    cannot be mistaken for a live rule (it was, on the first run of this check)."""
    return re.sub(r"/\*.*?\*/", lambda m: " " * len(m.group(0)), css, flags=re.S)


def _guard_span(css: str) -> tuple[int, int]:
    """Character span of the `prefers-reduced-motion: no-preference` block."""
    stripped = _strip_comments(css)
    start = stripped.index("{", stripped.index("@media (prefers-reduced-motion: no-preference)"))
    depth, i = 0, start
    while True:
        if stripped[i] == "{":
            depth += 1
        elif stripped[i] == "}":
            depth -= 1
            if depth == 0:
                return start, i
        i += 1


# --- the motion layer is wired up at all ---


def test_both_staff_portals_load_the_motion_layer_after_shared_css():
    for name, html in (("medic", MEDIC), ("doctor", DOCTOR)):
        assert "/shared/motion.css" in html, f"{name} does not load motion.css"
        # Order matters: motion.css overrides shared.css defaults (body height,
        # queue-item chrome). Loaded first, several rules would lose the cascade.
        assert html.index("/shared/shared.css") < html.index("/shared/motion.css"), name


def test_the_kiosk_does_not_pay_for_staff_chrome():
    """The patient portal has its own motion language and must not load this file."""
    assert "/shared/motion.css" not in _served("/kiosk.html")


# --- accessibility: motion is optional by construction ---


def test_every_animation_lives_behind_the_reduced_motion_guard():
    stripped = _strip_comments(MOTION)
    lo, hi = _guard_span(MOTION)
    stray = [
        stripped[:m.start()].count("\n") + 1
        for m in re.finditer(r"animation\s*:", stripped)
        if not (lo < m.start() < hi)
    ]
    assert not stray, f"animation declared outside the reduced-motion guard, line(s) {stray}"


def test_every_keyframes_lives_behind_the_reduced_motion_guard():
    stripped = _strip_comments(MOTION)
    lo, hi = _guard_span(MOTION)
    stray = [
        stripped[:m.start()].count("\n") + 1
        for m in re.finditer(r"@keyframes", stripped)
        if not (lo < m.start() < hi)
    ]
    assert not stray, f"@keyframes outside the reduced-motion guard, line(s) {stray}"


def test_only_transform_and_opacity_are_animated():
    """Composited properties only — the project's hardware has no discrete GPU, and
    animating layout properties on a 50-row queue is what makes a portal feel slow."""
    stripped = _strip_comments(MOTION)
    lo, hi = _guard_span(MOTION)
    for match in re.finditer(r"@keyframes\s+\w+\s*\{", stripped):
        if not (lo < match.start() < hi):
            continue
        depth, i = 0, match.end() - 1
        while True:
            if stripped[i] == "{":
                depth += 1
            elif stripped[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        body = stripped[match.end():i]
        animated = set(re.findall(r"(?m)^\s*([a-z-]+)\s*:", body))
        allowed = {"transform", "opacity", "box-shadow", "background-position"}
        assert animated <= allowed, f"{match.group(0)} animates {animated - allowed}"


# --- role separation: the two portals must not grow each other's workflow ---


def test_the_medic_portal_holds_no_doctor_workflow():
    for forbidden in ("/prescription", "/assistant/", "/review", "/history", "history-card"):
        assert forbidden not in MEDIC, f"doctor-only surface leaked into the medic portal: {forbidden}"


def test_the_doctor_portal_holds_no_medic_workflow():
    for forbidden in ("/assign", "/handoff", "dashboard/stats", "intake-card"):
        assert forbidden not in DOCTOR, f"medic-only surface leaked into the doctor portal: {forbidden}"


def test_each_portal_declares_its_own_role_identity():
    assert 'class="portal-medic"' in MEDIC and 'class="portal-doctor"' not in MEDIC
    assert 'class="portal-doctor"' in DOCTOR and 'class="portal-medic"' not in DOCTOR
    # And the stylesheet gives those two body classes visibly different chrome, so
    # the portals cannot read as the same screen with a different title.
    assert "body.portal-medic .portal-header" in MOTION
    assert "body.portal-doctor .portal-header" in MOTION
    assert "'TRIAGE'" in MOTION and "'CLINICAL'" in MOTION


# --- the queue reads server-derived facts, never its own ---


def test_the_queue_renders_the_server_derived_columns():
    for field in ("waiting_minutes", "fields_filled", "fields_total", "red_flags"):
        assert field in STAFF_JS, f"queue rows do not use {field}"
    assert "scope: queueScope" in STAFF_JS or "scope=" in STAFF_JS


def test_the_queue_does_not_recompute_the_tier_or_the_wait():
    """The row must not derive urgency of its own: two places computing 'how urgent'
    is how a queue starts disagreeing with the case it opens (the S35 lesson)."""
    assert "Date.now()" not in STAFF_JS
    assert "TIER_ORDER" not in STAFF_JS   # ordering is the server's, not the row's


def test_the_medic_attributes_its_referral():
    """audit_log recorded which doctor RECEIVED a case and never which medic sent it."""
    assert "editor_id: PORTAL.userId" in MEDIC
    assert "/assign" in MEDIC


def test_the_handoff_check_never_disables_the_forward_button():
    """The safety property of ADR-0058: a Critical patient must reach a doctor even
    with incomplete paperwork, so readiness may not gate the control."""
    assert "submitForward()" in MEDIC
    forward = MEDIC[MEDIC.index("async function submitForward"):]
    forward = forward[: forward.index("\n    }")]
    # Only the code that runs BEFORE the POST can prevent it. Clearing the readiness
    # afterwards is teardown, and pinning the whole function would forbid that too.
    before_post = forward[: forward.index("/assign")]
    assert "currentHandoff" not in before_post, "the forward path must not consult the readiness"
    assert "ready" not in before_post, "the forward path must not gate on readiness"


# --- rule #1 in the doctor's timeline ---


def test_the_timeline_carries_no_transcript():
    """Prior words are read by OPENING the prior visit, from the one stored copy."""
    history = DOCTOR[DOCTOR.index("function renderHistory"):]
    history = history[: history.index("function updatePlaceholders")]
    for forbidden in ("raw_text", "corrected_text", "utterances"):
        assert forbidden not in history, f"the timeline renders {forbidden}"
    # It links to the real visit instead.
    assert "openCase(v.visit_uuid)" in history


def test_the_timeline_writes_patient_text_with_textcontent():
    """Patient- and doctor-supplied strings never reach innerHTML (the portals'
    standing XSS rule); only fixed chrome is built as markup."""
    history = DOCTOR[DOCTOR.index("function renderHistory"):]
    history = history[: history.index("function updatePlaceholders")]
    for assignment in ("problem.textContent", "meds.textContent", "dx.textContent",
                       "date.textContent", "meta.textContent"):
        assert assignment in history, f"{assignment} missing — dynamic text must use textContent"


def test_status_codes_are_labelled_not_printed_raw():
    """ADR-0030 f: codes on the wire, labels in the frontend. The first draft of the
    timeline printed the raw schema code `awaiting_doctor` at a doctor."""
    assert "STATUS_LABELS" in DOCTOR
    assert "statusLabel(v.status)" in DOCTOR


def test_review_controls_are_hidden_once_a_case_is_reviewed():
    """POST /review 409s on a reviewed visit, so offering the button was offering an
    error — while the prescription form stays valid and must remain reachable."""
    assert "function renderReviewBar" in DOCTOR
    bar = DOCTOR[DOCTOR.index("function renderReviewBar"):]
    bar = bar[: bar.index("\n    }")]
    assert "'reviewed'" in bar and "'closed'" in bar
    assert "btn-accept" in bar and "btn-override" in bar
    assert "openPrescription" not in bar, "the prescription button must stay available"
