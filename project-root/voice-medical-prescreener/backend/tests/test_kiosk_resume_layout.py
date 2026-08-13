"""S36 / Finding 1 (ADR-0057) — the review layout must survive the final question.

The reported symptom: when the resume dock appears on the review screen ("শেষ করার আগে
আরও কয়েকটি প্রশ্ন" / "কোন তথ্যটি ঠিক করতে চান?"), the alignment breaks.

The cause was NOT the dock. It was the review grid behind it. S34's ``setResumeMode()``
hides ``#summary-float`` so only one assistant is on screen — but a grid item that is
``display: none`` stops being PLACED while its TRACK stays exactly where it was. Auto-
placement then dropped ``.summary-grid`` into the narrow first column and left the wide
one empty.

⚠ Measured in a real browser engine at 730x694, before the fix:

    float visible      cols "170px 471px"   grid x=216 w=471   card w=231
    resume dock open   cols "170px 471px"   grid x=28  w=170   card w=231  <-- overflows

The card was 61px WIDER than the column containing it, and the whole review jumped 188px
to the left. After the fix the same probe reports ``cols "659px"``, ``grid w=659`` and
``card w=322``, and closing the dock restores ``170px 471px`` exactly — so the change is
reversible, not a one-way collapse.

A second, smaller defect was found by the same probe and is fixed here too: the text
column between the avatar and the 🔊 was an inline ``flex:1`` with no ``min-width: 0``.
Every real Bangla and English question wrapped correctly, but one unbroken 76-character
token pushed the 🔊 button clean out of the row and made the dock scroll sideways.

⚠ Scope (the S28 convention): static-source assertions over the served kiosk.js /
kiosk.html, plus the browser geometry quoted above. No microphone is involved in this
finding at all — it is pure layout.
"""

import re

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def kiosk_js() -> str:
    resp = client.get("/kiosk.js")
    assert resp.status_code == 200
    return resp.text


def kiosk_html() -> str:
    resp = client.get("/kiosk.html")
    assert resp.status_code == 200
    return resp.text


def fn_body(name: str) -> str:
    js = kiosk_js()
    marker = f"function {name}("
    assert marker in js, f"{name}() is gone from the shipped kiosk"
    return js.split(marker)[1].split("\n}")[0]


def top_level_css() -> str:
    """The page CSS with every @media block removed — what applies at any size."""
    css = kiosk_html().split("<style>")[1].split("</style>")[0]
    return re.sub(r"@media[^{]*\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}", "", css)


# --- the grid track that outlived its occupant ---


def test_hiding_the_float_also_removes_its_column():
    """The whole fix in one assertion: there is a rule that collapses the review to a
    single column, and it is keyed to the same condition that hides the float."""
    css = top_level_css()
    assert ".summary-body.no-float { grid-template-columns: minmax(0, 1fr); }" in css


def test_the_two_halves_of_hiding_the_float_are_written_together():
    """Pins the PAIRING, which is the thing that can rot. Hiding the float and dropping
    its track are one decision; if a later session changes one line and not the other,
    the review silently goes back to rendering its cards in a 170px column."""
    body = fn_body("setResumeMode")
    assert "float.style.display = state.resumeActive ? 'none' : '';" in body
    assert "layout.classList.toggle('no-float', state.resumeActive);" in body


def test_the_collapsed_column_outranks_both_responsive_overrides():
    """`.summary-body.no-float` is (0,2,0) and every media-query rule for the same
    element is (0,1,0). Media queries add no specificity, so the single-column form wins
    at EVERY width without depending on source order — which is what makes this fix hold
    on the short-screen (max-height: 820px) and narrow (max-width: 620px) paths that
    each rewrite `grid-template-columns` for their own reasons."""
    html = kiosk_html()
    short = html.split("@media (max-height: 820px) {")[1].split("\n    }")[0]
    assert "grid-template-columns: 170px minmax(0, 1fr)" in short
    # …and neither override is itself specific enough to beat the collapsed form.
    assert ".summary-body.no-float" not in short


def test_the_single_column_form_still_uses_a_shrinkable_track():
    """minmax(0, 1fr), not a bare 1fr — the same reason the two-column form does. A
    bare `1fr` cannot go below its content's min-content width, so one wide card would
    push the review sideways instead of wrapping inside it."""
    css = top_level_css()
    rule = css.split(".summary-body.no-float {")[1].split("}")[0]
    assert "minmax(0, 1fr)" in rule
    assert "grid-template-columns: 1fr;" not in rule


# --- the question row: avatar | text | speaker ---


def test_the_question_text_column_can_actually_shrink():
    """`min-width: 0` is the load-bearing half. A flex item defaults to `min-width:
    auto`, which refuses to shrink below min-content — measured: one unbroken 76-char
    token pushed the 🔊 out of the row and the dock scrolled sideways."""
    css = top_level_css()
    rule = css.split(".resume-q-body {")[1].split("}")[0]
    assert "min-width: 0" in rule
    assert "flex: 1" in rule


def test_the_question_row_no_longer_carries_the_inline_flex():
    """The inline `style="flex:1"` could not be given `min-width: 0`, which is why the
    column moved into CSS. If the inline one comes back, the fix is dead."""
    html = kiosk_html()
    row = html.split('<div class="resume-q-row">')[1].split("</div>\n        <div class=\"dock-transcript\"")[0]
    assert 'class="resume-q-body"' in row
    assert 'style="flex:1;"' not in row


def test_a_long_unbroken_question_wraps_instead_of_overflowing():
    css = top_level_css()
    rule = css.split(".resume-question {")[1].split("}")[0]
    assert "overflow-wrap: anywhere" in rule


def test_the_avatar_and_the_speaker_button_never_absorb_the_shrink():
    """Both must keep their size while the TEXT column gives way — a squashed avatar or
    a 🔊 under 44px would be the same bug wearing a different hat. Measured at 730x694
    and 375x812, in Bangla and English, across four question lengths: avatar 64px and
    button 44px in all eight combinations."""
    css = top_level_css()
    assert "flex: none" in css.split(".bubble-speak {")[1].split("}")[0]
    assert "flex: none" in css.split(".doctor-avatar {")[1].split("}")[0]
