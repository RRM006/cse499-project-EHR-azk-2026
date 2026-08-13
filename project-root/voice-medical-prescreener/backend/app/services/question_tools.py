"""S36 (ADR-0057) — the session-scoped context tools behind an M7 question.

⚠ READ THIS FIRST: **these are not MCP tools, and that is a decision, not an omission.**
ADR-0057 records it in full; the short version is four facts about this codebase:

  1. **There is no tool-calling loop to attach a protocol to.** ``call_module()`` makes a
     ONE-SHOT ``system`` + ``user`` request to an OpenAI-compatible endpoint and returns
     the text. MCP presumes an agent that can call a tool, read the result and call
     again. Building that loop would multiply every M7 question by several round-trips.
  2. **Those round-trips are the scarce resource.** The whole AI strategy (ADR-0026)
     exists to spread ~1,000-1,500 free requests/day across three buckets. M7 sits in the
     live loop, so it is the worst possible place to spend 3-4 calls where 1 will do.
  3. **A second context path is the defect class this project keeps fixing.** S35 built
     ``collected_context()`` as the EXACT mirror of ``missing_summary_fields()`` so the
     two could never disagree. An MCP server assembling context its own way would
     recreate exactly that disagreement, one layer further from the tests.
  4. **Session scoping here is structural, and MCP would weaken it.** Every function
     below takes ``visit`` and reads only rows joined to it — a function that is not
     given visit B cannot return visit B, and no cache, session id or transport sits in
     between to get that wrong. Moving the boundary into a server makes it a RUNTIME
     property enforced by parameter passing over a wire, which is strictly weaker than a
     property enforced by the call signature.

So the three responsibilities the tools would have had are implemented here as three
small, explicit, individually testable functions, with the narrow contracts an MCP tool
would have declared — and none of the transport.

    get_patient_context   -> the minimum permitted identity context for THIS visit
    get_question_context  -> what is needed to decide what to ask next
    unsafe_question_reason-> the output guard M7's answer must pass before a patient
                             ever hears it

⚠ On what these tools are NOT allowed to become: they restate what the patient said and
what is still missing. They rank nothing, name no condition and choose no next field —
that stays with the M6 gap list and the server-named field (ADR-0052, ADR-0056). Rule #2
is a property of the architecture here, not a request in a prompt.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.app.db.models import CaseProfile, Patient, Visit
from backend.app.db.repository_visits import list_visit_utterances

#: How many of the most recent turns M7 is shown. The brief's rule — "prefer
#: deterministic/context-controlled inputs over blindly sending large conversation
#: history" — and a real robustness bound: before this, the ENTIRE conversation went into
#: every M7 prompt, so prompt size grew without limit as the loop ran. A full screening is
#: roughly 18 turns (4 scripted questions + answers, then the M7 loop), so this never
#: truncates a normal visit; it caps a pathological one before it can hit a free-tier
#: token limit and fail the question outright.
MAX_CONTEXT_TURNS = 24

#: Longest single collected value handed back as context (mirrors followup.py).
_COLLECTED_VALUE_CHARS = 160


def get_patient_context(db: Session, visit: Visit, profile: CaseProfile) -> dict:
    """Tool 1 — the MINIMUM permitted context about the patient of *this* visit.

    Exactly three facts, and each one exists because it changes what a good question
    looks like: ``age`` (never ask a child about age-related conditions, or an elderly
    patient about school), ``sex`` (so pregnancy-adjacent questions only go where they
    could apply), and ``area`` (so the question stays on the body region the patient
    came about instead of wandering).

    Everything else the ``patients`` row holds — name, phone, weight, BP — is
    deliberately NOT returned. A follow-up question never needs them, and the smallest
    context that can do the job is the one that cannot leak anything else.

    Session scoping is by construction: ``visit.patient_id`` is the only patient this
    can reach. Values are what the patient themselves said (``apply_demographics``
    stores nothing it was not told); a missing value is ``None`` and is rendered as
    nothing at all, because an empty "Age:" line invites a model to fill it in.
    """
    context: dict = {"age_years": None, "sex": None, "area": None}

    patient = db.get(Patient, visit.patient_id) if visit.patient_id else None
    if patient is not None and patient.birth_year:
        age = datetime.now(timezone.utc).year - patient.birth_year
        if 0 < age < 130:
            context["age_years"] = age
            # Sex only travels WITH a usable age, exactly as the previous renderer did:
            # it is there to make an age-appropriate question, not to describe a patient.
            if patient.sex:
                context["sex"] = patient.sex

    area = (profile.entities or {}).get("problem_area") or {}
    area_text = str(area.get("en") or area.get("bn") or "").strip()
    if area_text:
        context["area"] = area_text
    return context


def get_question_context(
    db: Session,
    visit: Visit,
    profile: CaseProfile,
    *,
    missing: list[str] | None = None,
) -> dict:
    """Tool 2 — everything needed to decide what to ask next, for *this* visit only.

    ``collected``     what the patient has already told us, per field (never re-ask it)
    ``missing``       the still-empty fields (the caller may override with its own list)
    ``already_asked`` the exact questions already put, so none is repeated
    ``turns``         the recent conversation, BOUNDED (see MAX_CONTEXT_TURNS)
    ``truncated``     whether anything was dropped, so the caller can be honest about it

    Every value is read through ``visit.id``. There is no cross-visit query here and no
    shared state to hold one — which is what makes "patient A's context cannot reach
    patient B's question" a property of the code rather than a promise.
    """
    from backend.app.services.completion import field_has_text
    from backend.app.schemas.profile import SUMMARY_FIELD_KEYS
    from backend.app.services.followup import questions_asked

    fields = ((profile.entities or {}).get("summary_fields")) or {}
    collected: dict[str, str] = {}
    for key in SUMMARY_FIELD_KEYS:
        field = fields.get(key)
        if not field_has_text(field):
            continue
        for slot in ("value_en", "value_bn", "value"):
            value = str((field or {}).get(slot) or "").strip()
            if value:
                collected[key] = value[:_COLLECTED_VALUE_CHARS]
                break

    if missing is None:
        missing = [k for k in SUMMARY_FIELD_KEYS if not field_has_text(fields.get(k))]

    utterances = list_visit_utterances(db, visit_id=visit.id)
    kept = utterances[-MAX_CONTEXT_TURNS:]
    turns = [
        {
            "speaker": "ASSISTANT" if u.role == "system" else "PATIENT",
            # Corrected text is preferred and is only ever READ (rule #1: the raw row is
            # untouched by anything in this module).
            "text": u.corrected_text or u.raw_text,
        }
        for u in kept
    ]

    return {
        "collected": collected,
        "missing": list(missing),
        "already_asked": [q.question_text for q in questions_asked(db, visit_id=visit.id)],
        "turns": turns,
        "truncated": len(utterances) > len(kept),
    }


def conversation_text(context: dict) -> str:
    """The bounded ``turns`` rendered the way M7 has always seen a conversation."""
    return "\n".join(f"{t['speaker']}: {t['text']}" for t in context["turns"])


# --- Tool 3: the output guard -------------------------------------------------------
#
# The system prompt has always told M7 never to diagnose. This CHECKS it. The difference
# matters: a prompt is a request to a model that may be swapped, degraded, quota-shifted
# to a weaker fallback (ADR-0026 routes M7 across three providers) or simply have a bad
# day, whereas this runs on every question on the way out and cannot be talked out of it.
#
# ⚠ Scope, stated honestly because a guard that is trusted for more than it does is worse
# than no guard: this is a HIGH-PRECISION, LOW-RECALL check. It catches the things that
# are unambiguously wrong in a QUESTION and nothing else. It is not a medical-safety
# classifier and must never be described as one — rule #2 rests on the whole design (no
# diagnosis is ever requested, stored or displayed), not on this function.
#
# Deliberately NOT banned: the words "ওষুধ" / "medicine" / "symptom" / "diagnosis" on
# their own. "আপনি কি কোনো ওষুধ খাচ্ছেন?" ("are you taking any medicine?") and "have you
# had a diagnosis before?" are exactly the questions M7 SHOULD be asking, and a guard
# that blocked them would quietly delete the useful half of the module.

#: A dosage amount. A follow-up question never needs to state one — asking "how many
#: milligrams do you take?" does not require the model to name a number itself, and a
#: number+unit in generated text is the single clearest sign it has started prescribing.
_DOSAGE = re.compile(
    r"\d+\s*(?:mg|mcg|ml|gm?|iu|মিগ্রা|মিলিগ্রাম|গ্রাম)\b", re.IGNORECASE
)

#: Assertions and instructions that cannot be part of an information-gathering question.
#: Each is a PHRASE, not a word, which is what keeps the false-positive rate down.
_ASSERTIONS = (
    # prescribing
    "you should take", "you must take", "you need to take", "i recommend",
    "i suggest you take", "i advise you to take", "please take this",
    "start taking", "stop taking your", "i prescribe", "prescription for you",
    # diagnosing
    "you have been diagnosed with", "you are suffering from", "i think you have",
    "you probably have", "it is likely that you have", "this is probably",
    "you seem to have", "my diagnosis", "the diagnosis is",
    # Bangla imperatives — high precision: each is an instruction to take something,
    # which a question is never allowed to be.
    "সেবন করুন", "খেয়ে নিন", "ওষুধটি খান", "ট্যাবলেট খান", "সেবন করবেন",
    "আপনার রোগ হয়েছে", "আপনি আক্রান্ত",
)


def unsafe_question_reason(question: str) -> str | None:
    """Why this generated question must not be asked, or ``None`` if it is fine.

    Returns a short machine-ish reason (``"dosage"``, ``"assertion:<phrase>"``) so the
    caller can log WHY it fell back — a guard that trips silently is a guard nobody ever
    discovers is misfiring.
    """
    text = str(question or "")
    if not text.strip():
        return "empty"
    if _DOSAGE.search(text):
        return "dosage"
    lowered = text.lower()
    for phrase in _ASSERTIONS:
        if phrase in lowered:
            return f"assertion:{phrase}"
    return None


def safe_fallback_question(target_key: str | None, field_prompts: dict[str, str]) -> str:
    """A deterministic, server-authored question for when the model's one is rejected.

    LOCAL and bilingual, in M7's own "Bangla (English)" shape. The patient is never left
    without a next question because the guard fired — the turn continues, it just
    continues with a question this repository wrote rather than one a model did.
    """
    if target_key and target_key in field_prompts:
        return (
            f"অনুগ্রহ করে আরও একটু বলুন — {field_prompts[target_key]} "
            f"(Please tell me a little more about {field_prompts[target_key]}.)"
        )
    return (
        "আপনার সমস্যাটি নিয়ে আর কিছু বলতে চান? "
        "(Is there anything else about your problem you would like to tell me?)"
    )
