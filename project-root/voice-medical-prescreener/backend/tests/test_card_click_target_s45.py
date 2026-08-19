"""S45 — "clicking ✏️ Edit does nothing" was the CARD MOVING BETWEEN mousedown AND mouseup.

WHAT WAS ACTUALLY WRONG, measured with real mouse events and a capture-phase listener
on the shipped portal. Aiming at the Edit button's own centre (from its own
``getBoundingClientRect``) produced this:

    pointerdown @628,526 -> DIV
    mousedown   @628,526 -> DIV
    mouseup     @628,526 -> BUTTON#intake-toggle      <-- a DIFFERENT element
    click       @628,526 -> DIV

`mousedown` and `mouseup` landed on **different elements**, and the browser's rule for
that is to fire ``click`` on their nearest common ancestor — the wrapper ``<div>``. The
button's own handler therefore never ran: no request, no error, nothing on screen. From
the medic's side it is a dead button, which is exactly how it was reported.

WHY THE ELEMENT UNDER THE POINTER CHANGED. ``.fx-card`` sat inside
``.fx-scene { perspective: 1400px }`` and carried ``transform-style: preserve-3d`` plus
``will-change: transform``. Hovering it applied ``translate3d(0, -2px, 12px)``; PRESSING
it applied ``translate3d(0, 0, 2px)``. Under a perspective, changing Z rescales the
element about the perspective origin, so that 10px of Z moved every child of the card by
a few pixels — during the press. A control near the card's edge slides out from under a
stationary pointer, between the two halves of a single click.

A/B PROVED IN THE BROWSER: re-injecting the old rule reproduced the split
mousedown/mouseup and the editor stayed shut; removing it again delivered all four
events to ``BUTTON#intake-toggle`` and the editor opened.

THE FIX is to stop moving a card that contains controls. The depth affordance S37 wanted
is kept and is carried by the ELEVATION SHADOW, which is what the ``--elev-*`` tokens are
for. Nothing was removed from the UI, no handler was rewired, no markup changed.

These tests pin that, because the failure mode is invisible in review: the CSS looks
tasteful, the handler looks correct, and only a real mouse finds the bug.

No JS test runner exists in this project (the S28 decision), so these are static-source
assertions over the SERVED stylesheet — the same method as the whole test_kiosk_* and
test_staff_portal_* family.
"""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def served(path: str) -> str:
    resp = client.get(path)
    assert resp.status_code == 200, f"{path} -> {resp.status_code}"
    return resp.text


MOTION = served("/shared/motion.css")


def strip_comments(css: str) -> str:
    """Blank out /* ... */ so a phrase quoted in a comment cannot be read as a live
    rule — this file's own comment block names every banned property."""
    return re.sub(r"/\*.*?\*/", lambda m: " " * len(m.group(0)), css, flags=re.S)


LIVE = strip_comments(MOTION)


def rules_for(selector_fragment: str) -> list[str]:
    """Every live declaration block whose selector list mentions the fragment."""
    out = []
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", LIVE):
        selector, body = match.group(1), match.group(2)
        if selector_fragment in selector:
            out.append(body)
    return out


# --- 1. the card that holds controls must not move -----------------------------------


def test_the_card_is_never_given_a_transform():
    """The root cause in one assertion. Any transform on .fx-card moves every control
    inside it; a transform that changes on :active moves them mid-click."""
    offenders = [b.strip() for b in rules_for(".fx-card") if "transform:" in b]
    assert not offenders, (
        "a .fx-card rule sets `transform` again — a control inside it can now slide "
        f"between mousedown and mouseup: {offenders}"
    )


@pytest.mark.parametrize("banned", ["translate3d", "translateZ", "preserve-3d"])
def test_no_three_dimensional_promotion_on_the_card(banned):
    """Z is the specific ingredient: under `.fx-scene`'s perspective it RESCALES the
    card, so the shift is proportional to a child's distance from the origin and lands
    differently on every button."""
    assert not [b for b in rules_for(".fx-card") if banned in b], f"{banned} is back on .fx-card"


def test_the_card_is_not_forced_onto_its_own_compositor_layer():
    assert not [b for b in rules_for(".fx-card") if "will-change" in b]


def test_the_card_only_transitions_box_shadow():
    """If `transform` is transitionable here again, someone has re-added the movement."""
    base = [b for b in rules_for(".fx-card") if "transition:" in b]
    assert base, ".fx-card lost its transition entirely"
    for body in base:
        transition = body.split("transition:")[1].split(";")[0]
        assert "transform" not in transition, f"transform is animatable again: {transition}"
        assert "box-shadow" in transition


# --- 2. …and the affordance it replaced must still be there ---------------------------


@pytest.mark.parametrize("state", [":hover", ":active", ":focus-visible"])
def test_the_card_still_responds_in_every_state(state):
    """The fix is 'convey depth with the shadow', NOT 'delete the feedback'. A medic
    must still see the card answer the pointer, and a keyboard user must still see
    focus."""
    bodies = rules_for(f".fx-card{state}")
    assert bodies, f".fx-card{state} was removed — the affordance is gone, not fixed"
    assert any("box-shadow" in b for b in bodies), f".fx-card{state} no longer signals anything"


def test_focus_visible_still_carries_the_focus_ring():
    bodies = rules_for(".fx-card:focus-visible")
    assert any("--elev-focus" in b for b in bodies)


# --- 3. what deliberately did NOT change ----------------------------------------------


def test_queue_rows_keep_their_two_dimensional_slide():
    """`.queue-item` is a single click target with no nested controls, so moving it
    cannot separate a mousedown from a mouseup on a child. It is untouched on purpose —
    the fix is scoped to containers of controls, not to all motion."""
    assert [b for b in rules_for(".queue-item:hover") if "translateX" in b]


def test_buttons_keep_their_own_lift():
    """`.fx-lift` moves the button ITSELF by 1px. The pointer stays inside a 33px-tall
    target, and mousedown/mouseup still land on the same element — that was never the
    defect and it is not what was changed."""
    assert [b for b in rules_for(".fx-lift:hover") if "translateY" in b]


def test_the_scene_keeps_its_perspective():
    """Perspective on the container is not itself the bug — a card that never moves in
    Z is never re-projected. Removing it would have been a wider change than the defect
    called for."""
    assert [b for b in rules_for(".fx-scene") if "perspective" in b]


# --- 4. the guarantee stated positively, across both portals --------------------------


def test_both_staff_portals_still_load_the_stylesheet_and_the_kiosk_does_not():
    for path in ("/medic/", "/doctor/"):
        assert "/shared/motion.css" in served(path), f"{path} no longer loads motion.css"
    assert "/shared/motion.css" not in served("/kiosk.html")


def test_the_intake_controls_are_still_plain_buttons_in_the_card():
    """Nothing about the fix moved the controls out of the card or rewired them — the
    same two buttons with the same ids still sit inside `#intake-card`."""
    medic = served("/medic/")
    assert 'id="intake-card"' in medic and "card fx-card" in medic
    assert 'id="intake-toggle"' in medic
    assert 'id="glucose-toggle"' in medic
    # …and they are still wired the way they always were (one handler each).
    assert medic.count("getElementById('intake-toggle').onclick") == 1
    assert medic.count("getElementById('glucose-toggle').onclick") == 1
