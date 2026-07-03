"""M10 red-flag rules (ADR-0024) — LOCAL, deterministic, no API.

This is the safety net that replaced the retired Emergency module: clearly
life-threatening symptom phrases FORCE the 'critical' tier no matter what the
model says (rule #3: surface red flags; never reassure falsely).

The check runs over BOTH raw and corrected text of every patient utterance
(raw is only read — rule #1), in Bangla, Banglish/Roman and English, matched
case-insensitively as substrings so dialect particles around them don't matter.
Recall over precision: a false Critical costs doctor attention; a miss costs a life.
Test TC-R1 (test_log.md): zero misses on the fixed phrase list.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.db.models import Visit
from backend.app.db.repository_visits import list_visit_utterances

# category -> trigger phrases (lowercase). Extend by ADDING phrases — additions are
# data-only and must come with a matching TC-R1 test case.
RED_FLAG_RULES: dict[str, list[str]] = {
    "chest pain": [
        "বুকে ব্যথা", "বুকের ব্যথা", "বুকে চাপ", "বুক ধড়ফড়",
        "buke betha", "buke bytha", "buke chap",
        "chest pain", "chest pressure", "pain in my chest", "pain in chest",
    ],
    "severe breathing difficulty": [
        "শ্বাসকষ্ট", "শ্বাস নিতে পারছি না", "নিঃশ্বাস নিতে কষ্ট", "দম বন্ধ",
        "shash koshto", "shas kosto", "nishash nite koshto", "dom bondho",
        "can't breathe", "cannot breathe", "difficulty breathing",
        "shortness of breath", "breathless",
    ],
    "stroke signs": [
        "মুখ বেঁকে", "কথা জড়িয়ে", "এক পাশ অবশ", "একদিক অবশ", "হাত-পা অবশ",
        "mukh beke", "kotha joriye", "ek pash obosh",
        "face drooping", "slurred speech", "one side numb", "one side weak",
        "one-sided weakness", "sudden numbness",
    ],
    "loss of consciousness": [
        "অজ্ঞান", "জ্ঞান হারিয়ে", "সেন্স হারিয়ে",
        "oggan", "gyan hariye", "sense hariye",
        "unconscious", "lost consciousness", "passed out", "fainted", "blacked out",
    ],
    "severe uncontrolled bleeding": [
        "রক্তক্ষরণ বন্ধ হচ্ছে না", "প্রচুর রক্ত",
        "onek rokto", "rokto bondho hocche na",
        "bleeding won't stop", "bleeding wont stop", "heavy bleeding",
        "coughing up blood", "vomiting blood", "রক্ত বমি", "কাশিতে রক্ত",
    ],
}


def scan_text(text: str) -> list[str]:
    """Red-flag categories triggered by one piece of text (each listed once)."""
    lowered = text.lower()
    return [
        category
        for category, phrases in RED_FLAG_RULES.items()
        if any(p in lowered for p in phrases)
    ]


def check_visit(db: Session, visit: Visit) -> list[str]:
    """All red-flag categories triggered anywhere in the visit's PATIENT speech
    (raw AND corrected text are both scanned; raw is read-only)."""
    found: list[str] = []
    for u in list_visit_utterances(db, visit_id=visit.id):
        if u.role != "patient":
            continue  # never trigger on the system's own spoken questions
        for text in (u.raw_text, u.corrected_text or ""):
            for category in scan_text(text):
                if category not in found:
                    found.append(category)
    return found
