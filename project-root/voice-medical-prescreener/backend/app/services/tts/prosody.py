"""S35 / Finding 6 — how a line is PACED before it is handed to a synthesizer.

The complaint was that the assistant "sounds robotic". Part of that is the engine and
is answered by ADR-0050 (neural `bn-BD` instead of espeak's formant synthesis). The
other part is not the engine at all: a synthesizer decides where to breathe from the
PUNCTUATION it is given, and the strings this project hands it are not written for
speech. An M7 question arrives as one line with the English half stripped off by
`spokenHalf()`, often leaving no terminator; a summary value is a fragment; a
recogniser transcript has no punctuation whatsoever. Handed a bare clause, every
engine — neural or not — reads it flat and clips the end.

So this module adds the two prosodic cues that cost nothing and cannot change meaning:

  1. a sentence-final terminator, so the engine applies a closing contour instead of
     stopping mid-breath (`।` for Bangla, `.` for English);
  2. a comma where the text already implies a pause — an em dash or an ellipsis, both
     of which this project's bilingual strings use freely and no engine reads as a
     pause.

⚠ WHAT THIS MUST NEVER DO. It must never change, add, remove or reorder a WORD. The
kiosk's read-back speaks the PATIENT's own captured words through this same path
(ADR-0055), and a "helpful" rewrite there would be reading back something they did not
say — the rule #1 failure this project exists to avoid. Punctuation and whitespace
only, and nothing at all is stored: this runs at the synthesis boundary, exactly like
`spokenHalf()`, and the stored/displayed text is untouched.
"""

from __future__ import annotations

import re

#: Characters an engine already treats as end-of-sentence. Includes the Bangla danda
#: (`।`) and its double form, plus the CJK full stop that occasionally survives a paste.
SENTENCE_ENDINGS = "।॥.!?…:;，,。"

#: Bangla gets a danda, English a full stop. Anything else would be read aloud as a
#: symbol by some engines rather than heard as a pause.
_TERMINATOR = {"bn": "।", "en": "."}

#: Dashes and ellipses THIS PROJECT's own strings use as pauses ("Listening — just
#: stop speaking", "Say the digits one at a time..."). No engine pauses on them.
_PAUSE_MARKS = re.compile(r"\s*(?:—|–|--|\.\.\.|…)\s*")


def speech_text(text: str, lang: str) -> str:
    """`text`, punctuated so it can be SPOKEN. Words are never touched.

    Returns the input unchanged when there is nothing safe to do (empty, or already
    ending in a terminator), so this is a no-op for text that was written for speech.
    """
    spoken = str(text or "").strip()
    if not spoken:
        return spoken
    # An implied pause becomes a real one. A comma, not a full stop: these marks join
    # clauses, and ending the sentence there would break the phrase in half.
    spoken = _PAUSE_MARKS.sub(", ", spoken)
    # Collapse the whitespace a stripped bilingual half or a transcript leaves behind —
    # a run of spaces is silent, but a newline mid-question makes some engines restart
    # their intonation as though a new sentence began.
    spoken = re.sub(r"\s+", " ", spoken).strip()
    # Never leave a doubled or dangling comma behind (", ।" reads as a stumble).
    spoken = re.sub(r",\s*(?=[" + re.escape(SENTENCE_ENDINGS) + r"])", "", spoken)
    spoken = spoken.rstrip(", ")
    if not spoken:
        return ""
    if spoken[-1] in SENTENCE_ENDINGS:
        return spoken
    return spoken + _TERMINATOR.get(lang, ".")
