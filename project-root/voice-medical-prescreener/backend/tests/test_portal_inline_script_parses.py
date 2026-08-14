"""S40 — the served portals' inline scripts must actually PARSE.

Why this file exists, stated plainly: S39 added a developer note inside
``renderPostReferral()``'s template literal, as an HTML comment, and the note named
the ``patients`` table **in backticks**. A backtick inside a template literal ends
it. The browser therefore read the next word as code and threw

    Uncaught SyntaxError: Unexpected identifier 'patients'

A syntax error is not a partial failure. The whole ``<script>`` block is discarded
before a single line of it runs, so **every function it declared was undefined**:
``login()`` never existed, which is why clicking "Login to Dashboard" /
"ড্যাশবোর্ডে প্রবেশ করুন" did nothing at all, and ``tickClock()`` never ran, which is
why the S38 header clock sat at its "—" placeholder. One character class, two
user-visible features gone, and a portal that could not be entered.

**Nothing in the 1005-test suite could see it.** Every frontend test in this project
is a static-source assertion (the S28 decision: no vitest, no jsdom), and the file
still *contained* every string those tests look for. The source was intact; only its
executability was gone. That is precisely the gap S39 wrote down for itself — "no
browser has rendered the new portal DOM" — and it is the gap this file closes.

Two layers, because they fail differently:

  1. :func:`test_no_backtick_in_an_html_comment_inside_an_inline_script` —
     dependency-free and always runs. It bans the exact construct that caused this.
     The portals do carry other HTML comments inside generated markup, and those are
     left alone: they are pre-existing, they are not what broke, and rewriting live
     markup to satisfy a test is a bigger change than the bug warrants. What is
     forbidden is the one character that can end a template literal from inside a
     comment the author believed was inert.

  2. :func:`test_every_portal_inline_script_parses` — the real check, run through
     ``node --check`` when node is on PATH, skipped with a reason when it is not.
     It catches ANY syntax error, not only this one. It is a skip rather than a hard
     dependency because the project must install and run from one requirements.txt on
     Windows and Arch (no Node in that file, and none is being added for a test).
"""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)

# Every served page that carries an inline <script>. The kiosk keeps all of its
# JavaScript in /kiosk.js (an external file node can check directly), but it is listed
# so that the day someone inlines a block into it, the block is covered from that day.
PORTAL_PAGES = ("/medic/", "/doctor/", "/kiosk.html")

# The external scripts the portals load. A syntax error here is the same outage: it
# takes out shared.js/staff.js/kiosk.js for every page that loads them at once.
PORTAL_SCRIPTS = (
    "/shared/shared.js",
    "/shared/staff.js",
    "/shared/tts.js",
    "/kiosk.js",
)


def _served(path: str) -> str:
    resp = client.get(path)
    assert resp.status_code == 200, f"{path} -> {resp.status_code}"
    return resp.text


def _inline_scripts(html: str) -> list[str]:
    """Every <script> block WITHOUT a src, in document order.

    Deliberately a plain scan rather than a regex over ``<script[^>]*>``: the opening
    tag of a block that has no ``src`` is exactly ``<script>`` in all three files, and
    a scan cannot be fooled by the string "</script>" appearing inside one.
    """
    blocks: list[str] = []
    cursor = 0
    while True:
        start = html.find("<script>", cursor)
        if start == -1:
            return blocks
        body_at = start + len("<script>")
        end = html.find("</script>", body_at)
        assert end != -1, "unclosed <script> block in the served page"
        blocks.append(html[body_at:end])
        cursor = end


def test_no_backtick_in_an_html_comment_inside_an_inline_script():
    """A backtick inside an HTML comment inside a <script> is how S40 got in.

    The medic portal's note read ``... the same `patients` row ...``. The author saw a
    comment; the parser saw the end of a template literal followed by the identifier
    ``patients``. Nothing about the surrounding code looked wrong, and no static-source
    assertion could tell — the file still contained every string the tests search for.

    So the rule is about the character, not the comment: **prose that names code goes
    in a /* */ comment, where a backtick is just a backtick.**
    """
    for page in PORTAL_PAGES:
        for index, block in enumerate(_inline_scripts(_served(page))):
            for comment in re.findall(r"<!--.*?-->", block, re.S):
                assert "`" not in comment, (
                    f"{page} inline script #{index + 1} has an HTML comment containing "
                    f"a backtick:\n{comment.strip()[:200]}\n"
                    "Inside a template literal that backtick ENDS the string and turns "
                    "the whole block into a SyntaxError, so every function it declares "
                    "is undefined and the portal cannot be entered (S40). Move the note "
                    "into a /* */ comment outside the literal."
                )


def _node_check(source: str, label: str) -> None:
    """Parse `source` with node, failing with node's own message and line."""
    with tempfile.TemporaryDirectory() as tmp:
        # Newlines are preserved as-is so node's reported line numbers line up with
        # the block; the caller pads the block to its offset in the original file.
        script = Path(tmp) / "block.js"
        script.write_text(source, encoding="utf-8")
        result = subprocess.run(
            ["node", "--check", str(script)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    assert result.returncode == 0, f"{label} does not parse:\n{result.stderr}"


@pytest.mark.skipif(
    shutil.which("node") is None,
    reason="node is not on PATH; the JS parse check needs it (see the module docstring)",
)
def test_every_portal_inline_script_parses():
    """The check that would have caught S40 before a human ever clicked the button."""
    for page in PORTAL_PAGES:
        html = _served(page)
        for index, block in enumerate(_inline_scripts(html)):
            # Pad with the newlines that precede the block so a failure reports the
            # line number in the HTML file, not in the extracted fragment.
            offset = html[: html.index(block)].count("\n")
            _node_check("\n" * offset + block, f"{page} inline script #{index + 1}")


@pytest.mark.skipif(
    shutil.which("node") is None,
    reason="node is not on PATH; the JS parse check needs it (see the module docstring)",
)
def test_every_shared_script_parses():
    """staff.js was truncated to zero bytes once (S39); it is load-bearing for both
    staff portals, and shared.js is load-bearing for all three."""
    for path in PORTAL_SCRIPTS:
        _node_check(_served(path), path)
