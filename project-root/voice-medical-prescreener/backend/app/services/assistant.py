"""M16 — the doctor-side AI drug-information assistant (P3-3, 2.0 build).

Web search (ddgs/DuckDuckGo — free, no key) + one LLM call on the Flash bucket,
answering the DOCTOR's drug question from the fetched snippets. Informational
only (rule #2): the MANDATORY disclaimer is attached SERVER-SIDE on every answer
— never trusted to the model — and the prompt forbids prescribing decisions.
The search receives only the doctor's typed question, never patient data
(rule #4); the endpoint is doctor-triggered, never automatic.

Search is best-effort: if DuckDuckGo is unreachable the model still answers from
general knowledge with an empty sources list (the UI says so). A total LLM
failure surfaces as LLMCallError for the route to turn into a 502.
"""

from __future__ import annotations

import json
import logging

from sqlalchemy.orm import Session

from backend.app.db.models import Visit
from backend.app.services.intake import _parse_json
from backend.app.services.llm_client import call_module

logger = logging.getLogger(__name__)

ASSISTANT_DISCLAIMER = "AI-generated information. Please verify before prescribing."
ASSISTANT_DISCLAIMER_BN = "এআই-উৎপাদিত তথ্য। প্রেসক্রাইব করার আগে অনুগ্রহ করে যাচাই করুন।"

_MAX_RESULTS = 5
_SNIPPET_CHARS = 400  # per-result cap keeps the prompt small (quota discipline)

_ANSWER_SYSTEM = (
    "You are a drug-information assistant for a licensed physician in Bangladesh. "
    "Answer the doctor's question about a medicine (uses, typical adult dosing "
    "ranges, contraindications, interactions, side effects, local availability) "
    "using the WEB SEARCH RESULTS provided, falling back to established "
    "pharmacological knowledge when they are thin. You provide INFORMATION ONLY: "
    "never recommend prescribing for a specific patient, never diagnose, and say "
    "so if asked. If the question is not about medicines or drug therapy, say you "
    "only answer drug-information questions. Return ONLY a JSON object: "
    '{"answer_en": "<concise answer in English, plain sentences>", '
    '"answer_bn": "<the same in Bangla script>"} — no extra keys.'
)


def _search(question: str) -> list[dict]:
    """Top DuckDuckGo hits for the doctor's question — {title, url, snippet} each.

    Best-effort: any failure (offline dev box, rate limit, API change) returns []
    so the assistant degrades to general-knowledge answers instead of erroring.
    """
    try:
        from ddgs import DDGS

        raw = DDGS().text(question, max_results=_MAX_RESULTS) or []
    except Exception as exc:  # noqa: BLE001 — search is optional by design
        logger.warning("M16 web search unavailable: %s", exc)
        return []
    results = []
    for r in raw:
        title = str(r.get("title") or "").strip()
        url = str(r.get("href") or "").strip()
        snippet = str(r.get("body") or "").strip()[:_SNIPPET_CHARS]
        if title or snippet:
            results.append({"title": title, "url": url, "snippet": snippet})
    return results


def answer_drug_question(
    db: Session, visit: Visit, question: str, language: str = "en"
) -> dict:
    """One M16 round-trip: search -> LLM -> answer dict with the disclaimer.

    Raises LLMCallError when the whole provider chain fails (route -> 502).
    """
    sources = _search(question)
    if sources:
        blocks = [
            f"[{i + 1}] {s['title']}\n{s['url']}\n{s['snippet']}"
            for i, s in enumerate(sources)
        ]
        context = "WEB SEARCH RESULTS:\n\n" + "\n\n".join(blocks)
    else:
        context = "WEB SEARCH RESULTS: (search unavailable — answer from established knowledge)"

    user = f"DOCTOR'S QUESTION:\n{question}\n\n{context}"
    reply = call_module(db, visit_id=visit.id, module_code="M16",
                        system=_ANSWER_SYSTEM, user=user)
    try:
        data = _parse_json(reply)
        answer_en = str(data.get("answer_en") or "").strip()
        answer_bn = str(data.get("answer_bn") or "").strip()
    except (json.JSONDecodeError, AttributeError):
        # Salvage a non-JSON reply as the English answer rather than failing the doctor.
        answer_en, answer_bn = reply.strip(), ""

    return {
        "answer_en": answer_en,
        "answer_bn": answer_bn,
        "sources": sources,
        # Rule #2: attached HERE on every response — never left to the model.
        "disclaimer": ASSISTANT_DISCLAIMER,
        "disclaimer_bn": ASSISTANT_DISCLAIMER_BN,
    }
