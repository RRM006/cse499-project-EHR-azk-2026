"""S42 — the ONE place an LLM provider failure becomes an HTTP response.

Why this file exists, stated plainly, because it is a safety boundary rather than a
tidiness one:

Every route that ran an LLM task used to answer ``HTTPException(502, detail=str(exc))``.
``str(exc)`` on an ``LLMCallError`` ends in the last provider's raw error body, and that
body was MEASURED during the S42 outage to contain::

    google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry
    shortly, or add your own key to accumulate your rate limits:
    https://openrouter.ai/settings/integrations  ... 'provider_name': 'Google AI Studio'

The kiosk pipes ``detail`` straight into its error banner, so a patient sitting in a
waiting room was shown the project's model id, its upstream provider's name, its
routing arrangement and a signup URL. None of that is the patient's business, none of
it helps them, and it is configuration disclosure from a system that handles medical
data. The technical text is not lost — it is already written to the server log AND to
a ``module_events`` row per attempt, which is where a developer looks.

``Retry-After`` is set because these failures are genuinely temporary and the header is
the standard way to say so to any client, including the ones we have not written.
"""

from __future__ import annotations

from fastapi import HTTPException

from backend.app.services.llm_client import LLMCallError

# Seconds. Matches the shortest provider cooldown (a plain RPM 429 clears inside a
# minute), so a client that honours the header retries at roughly the moment the
# quickest bucket comes back rather than while it is still cooling down.
RETRY_AFTER_SECONDS = 30


def llm_unavailable(exc: LLMCallError) -> HTTPException:
    """Map a dead provider chain to a patient-safe 502.

    502 is kept deliberately: it is the status this project has always used for "the
    upstream model could not be reached" (``test_assistant.py`` pins it), and the fix
    here is about the BODY, not the code. Changing both at once would have made a
    security fix look like an API change.
    """
    return HTTPException(
        status_code=502,
        detail=exc.safe_detail,
        headers={"Retry-After": str(RETRY_AFTER_SECONDS)},
    )
