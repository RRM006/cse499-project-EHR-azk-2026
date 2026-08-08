# 🗂️ BUILD TRACKER — "Context Fixed Problem 3.0" (next fix/feature cycle — AWAITING FINDINGS)

> **Why this file exists (created S24, 2026-07-11):** the 2.0 cycle
> (`context fixed problem 2.0.md`) is **fully complete** — STRUCT + P1 + P2 + P3 + P4 all ✅,
> 192 tests, Alembic head 0012. The human's next phase is **manual testing of the whole system**
> (the live real-mic run per `human_live_run_guide.md` + free exploration of all three portals).
> Bugs, UX friction and improvement ideas found during that testing land HERE, and this file
> becomes the single living checklist for the 3.0 cycle — exactly the workflow that made 2.0 work:
>
> 1. **The human pastes RAW findings** into the inbox below (any form: bullet notes, Bangla/English,
>    screenshots described in words, "this felt slow", half-formed ideas — no polish needed).
> 2. **Claude turns the raw notes into numbered, checkable items** (like STRUCT-n / P1-n … in 2.0):
>    each item gets an ID, a priority, the portal it touches, and the files involved — and the
>    human's original wording is kept verbatim below the tracker as the source of truth.
> 3. **The plan is approved by the human first** (an ADR in `decisions.md` if real decisions are
>    made), then executed **ONE item per human "go"**, functional fixes before UI polish.
>
> **Status: 🟡 BOTH ITEMS SHIPPED (S30, 2026-08-08) — awaiting ONE combined human live listen.**
> TTS-1 (bilingual split, ADR-0051) and TTS-2 (natural neural voice, ADR-0050 Accepted) are both
> implemented and tested; the cycle stays open until the human hears them together and either closes it
> or files new findings. (The faculty's **three** future
> requirements are NOT part of this cycle — quantized summary model, quantized STT/TTS, and the fully
> voice-driven follow-up loop live in `agent_docs/faculty_future_features.md`, a separate research
> track. In particular: "the mic needs two taps" is a **Req 3 research item, not a 3.0 bug** — do not
> file it here. ⚠ **TTS-2 below deliberately BLURS that line** and says so explicitly.)
>
> **Legend (same as 2.0):** ✅ done · ⏳ in progress · ⬜ not started · 👉 the next step

---

## 📥 RAW FINDINGS INBOX (human: paste here — any format, no polish needed)

> Tip from the 2.0 cycle: per finding, one line each for **where** (which portal/screen),
> **what happened / what you expected**, and **how bad** (blocker / annoying / nice-to-have)
> makes the triage fast — but plain unstructured notes are fine too.

### 📥 Finding set 1 — 2026-08-08 (S29), after the ADR-0049 Bangla TTS live run — VERBATIM

> "Bangla voice: Too robotic
> Mic timing: Pass
> Countdown: Pass
> Transcript clean: Yes
> English: Pass
> But there are no gap when tts Bangla and English hear . some time 2 question hear at a same time
> this is confusing . i want make it like human not too robotic and also want fixed some bug and add
> some features in upcoming session"

**What PASSED and is now settled (do not re-test or re-open):** mic timing (the echo guard — the mic
waits for the audio to finish), the S4 3-2-1 countdown, **transcript clean = zero AI words in the
patient's verbatim record (rule #1 holds end-to-end)**, and English TTS.

---

## Progress at a glance

| ID | What | Priority | Status |
|---|---|---|---|
| **TTS-1** | One question is spoken as Bangla + English back-to-back with no gap → sounds like two questions | 🔴 functional, do FIRST | ✅ **DONE (S30)** — human listen pending |
| **TTS-2** | espeak-ng Bangla is too robotic — needs a natural, human-sounding voice | 🟠 quality | ✅ **DONE (S30)** — human listen pending |

## Checklist (maps to the findings below)

### ✅ TTS-1 — "no gap between Bangla and English; sometimes two questions at once" — **FIXED (S30)**
> **Human decision: option (a) — speak ONLY the half matching the active UI language.** Option (b)
> (both halves with a real pause) was rejected: it costs ~1 s per question, against the "minimize
> waiting" priority. Recorded as **ADR-0051**.
>
> **Shipped (frontend only — 4 files, ~50 lines, no backend/schema/M7-contract change):**
> - `frontend_shared/tts.js` — a `BILINGUAL_QUESTION` regex + `spokenHalf(text, short)`, applied
>   ONCE inside `speak()` as `const speech = verbatim ? text : spokenHalf(text, short);`. **Both**
>   providers now receive `speech`: `new SpeechSynthesisUtterance(speech)` and
>   `encodeURIComponent(speech)` — the server path matters most, because on Windows it is the ONLY
>   Bangla route (ADR-0049), so splitting only the browser path would have left the defect live.
> - `frontend/kiosk.js` — one call site: the per-bubble 🔊 replay passes `verbatim: role === 'patient'`.
>   An assistant bubble replays the half the patient already heard; a **patient** bubble is the
>   patient's OWN captured words and is read back whole (reading back part of what someone said is a
>   rule #1 defect).
> - **Fails safe by design:** the pattern matches only a Bangla-script head followed by a TRAILING
>   parenthesised Latin-script tail. A monolingual parenthetical (`"fever (above 100F)"`), a Bangla
>   parenthetical, nested parens, or a `(...)` not at the very end all FAIL to match and are spoken
>   **whole**. When unsure it loses seconds, never words.
> - **Unchanged, and pinned by tests:** the stored `system` utterance (`raw_text: text`), the
>   on-screen bilingual bubble (ADR-0028 fallback), and `followup.py`'s M7 prompt.
> - **Tests: 277 → 297 pass, 0 skipped.** New `backend/tests/test_tts_bilingual_split.py` (20 tests)
>   **extracts the shipped regex literal out of the served `tts.js` and runs it**, so the rule is
>   exercised rather than asserted about. Two pre-existing static assertions in
>   `test_kiosk_auto_listen.py` / `test_kiosk_tts_fallback.py` were updated to the new strings with
>   their original intent kept (replay stays plain `speak()`, never `askAloud()`).
> - **Also verified in a real JS engine** (my split tests run the literal through Python's `re`):
>   `spokenHalf` in Chrome agrees case-for-case on 8 inputs, and with `serverTts` on + the UI in
>   Bangla, `/api/tts` was called with `lang=bn` and `text=আপনার জ্বর কত দিন ধরে?` — English half
>   absent. No console errors.
> - ⚠ **Still pending: the human has NOT heard it.** Tests prove which string reaches each provider;
>   only a live listen proves it sounds like one question. TTS-2 will still make that voice robotic.
- **Diagnosed, not guessed. Root cause was one line:** `backend/app/services/followup.py:45` forces the
  M7 prompt to emit `"question": "<Bangla question> (<English question>)"`. **Every question is a single
  string containing BOTH languages**, so TTS reads Bangla and then immediately English in one breath —
  which is exactly "no gap" and "two questions at the same time". It is one utterance, not an overlap.
- **Pre-existing since S25**, not caused by ADR-0049 — but ADR-0049 made it obvious, because espeak-ng
  with `-v bn` also applies Bengali phonetics to the English half, compounding the confusion.
- **Proposed fix (TTS-only, rule #1 safe):** speak only the half matching the active UI language, by
  splitting on the trailing `(...)` in `askAloud()`/`speak()`. ⚠ **The stored `system` utterance and the
  on-screen text MUST keep the full bilingual string unchanged** — this changes what is SPOKEN, never
  what is stored or displayed (`followup.py:145` stores `question_text` verbatim; ADR-0028 keeps the
  text as the fallback). Alternative if the human prefers hearing both: keep both halves but insert a
  real pause between them (two utterances, or an SSML-style break) — costs ~1 s per question, against
  the "minimize waiting" priority.
- ~~**Open question for the human:** only their language, or both with a pause?~~ **ANSWERED: (a),
  only the UI language.** See ADR-0051.
- Files touched: `frontend_shared/tts.js`, `frontend/kiosk.js`, `backend/tests/test_tts_bilingual_split.py`
  (new), plus two updated static assertions. `followup.py` was deliberately **NOT** touched — returning
  the halves as separate server fields would change the M7 contract and what medic/doctor display.

### ✅ TTS-2 — Bangla voice is "too robotic"; make it sound human — **FIXED (S30)**
> **Human decisions: (1) provider = `edge-tts` (Microsoft neural `bn-BD`), (2) on failure, fall back to
> espeak-ng rather than go silent.** Both recorded in **ADR-0050, now Accepted.**
>
> **⚠ A documented "fact" below was wrong and it flipped the comparison.** This file and ADR-0050 listed
> edge-tts's cost as a *"binary `aiohttp` dep"* and never checked its licence. Verified in S30:
> **edge-tts 7.2.8 is LGPL-3.0** — no copyleft on our code, **no non-commercial clause**; whereas
> **`facebook/mms-tts-ben` is CC-BY-NC-4.0**, which bars a real clinic deployment. The "safe local
> option" was the more restrictive one on licensing. (`requirements.txt` also already ships a binary dep
> via `ddgs`→`primp`, so `aiohttp` broke no property that was still intact.)
>
> **⚠ The rule #4 trade-off was accepted knowingly, not slipped in:** M7 questions are derived from what
> the patient said, and edge-tts sends that text to Microsoft. What tipped it: the system **already**
> sends the patient's *actual audio* to Google via the Web Speech API, so this adds a second processor of
> strictly less sensitive derived text. **It still limits what the thesis may claim about privacy.**
> Escape hatch for a private/offline deployment: `TTS_PROVIDER=espeak`.
>
> **Shipped (backend only — no route, frontend, schema or Alembic change):**
> - `backend/app/services/tts/edge.py` — `EdgeTtsProvider`, one subclass. `PROVIDER_FACTORIES` in
>   `service.py` gained one entry; `TTS_PROVIDERS` gained `"edge"`. **The seam held exactly as designed.**
> - **Fallback chain** in `synthesize()`: primary → espeak-ng → `TtsUnavailable`. Both failing names
>   BOTH providers in the error, still returns **503 never a silent 200**, and logs the fallback at
>   **WARNING** so a clinic can't run robotic for a week without noticing. `TTS_LOCAL_FALLBACK=false`
>   restores ADR-0049's bare-503 behaviour.
> - **MP3 needed no extra work** — the ABC already carries `media_type` per provider and `<audio>` plays
>   MP3 natively. Two generalisations were required: `MAX_TEXT_CHARS` moved `espeak.py` → `base.py` (it
>   is the endpoint's contract, not one engine's), and availability became `TtsProvider.available()`
>   instead of a duck-typed `resolve_binary` probe. `available()` never touches the network.
> - `requirements.txt` += `edge-tts==7.2.8`; `.env.example` documents `edge`/`espeak`/`browser`, the
>   voices, the rate, the timeout and the privacy warning.
> - **Tests: 297 → 318 pass, 1 skipped.** New `test_tts_edge_provider.py` (21) is **offline by default**
>   (a suite needing wifi fails in a lab); the one real network test is opt-in via `TTS_LIVE=1` and
>   passed. Three espeak-specific tests now pin `TTS_PROVIDER=espeak` explicitly — they used to rely on
>   it being the default and would otherwise have gone to the network and got MP3 instead of RIFF.
> - **Measured live through the running server:** `bn` and `en` both `audio/mpeg` in **~0.8 s**, playback
>   completed at **3013 ms**, `ttsSpeaking()` **true throughout** (S3 echo guard still holds against
>   network latency — rule #1), and `<audio>` requested **only the Bangla half**, proving TTS-1 + TTS-2
>   compose.
> - ⚠ **Naturalness is NOT proven by any of this.** Bytes, MIME, latency and completed playback are
>   measured; whether it sounds human is the human's ears.
- The human's verdict on ADR-0049's known trade-off. espeak-ng is a formant synthesizer, so this is
  **inherent, not tunable** — `TTS_SPEED_WPM` and voice variants change speed/pitch, not naturalness.
  **The seam built in S29 is the right architecture; only the PROVIDER needs replacing** — that is one
  new subclass in `backend/app/services/tts/`, no route or frontend change (see ADR-0050, Proposed).
- Candidate providers, already researched in S29 (ADR-0049's rejected list) — **not yet chosen:**
  | Option | Bangla quality | Cost |
  |---|---|---|
  | **edge-tts** (`bn-BD-NabanitaNeural`, `bn-BD-PradeepNeural`) | genuinely neural, natural Dhaka accent | adds binary `aiohttp` dep; **sends question text to Microsoft**; needs internet |
  | **`facebook/mms-tts-ben`** | real neural VITS, local/offline | torch+transformers (heavy); **CC-BY-NC-4.0** = non-commercial only |
  | **Edge browser** | Microsoft online `bn-BD` voices, zero code | per-machine host setup; helps neither Chrome nor a reproducible demo; **unverified** |
- ⚠ **Overlaps faculty Requirement 2** (quantized on-device Bangla STT/TTS) — that research track is
  the "proper" long-term answer and now has a seam waiting for it. Decide next session whether TTS-2 is
  a 3.0 quick win (edge-tts) or gets folded into Req 2.
- ⚠ **Rule #4 tension to settle explicitly:** M7 questions are DERIVED from what the patient said, so a
  cloud TTS exports patient-derived content to a third party. This is precisely why ADR-0049 chose a
  local engine. Choosing edge-tts means consciously accepting that trade-off for naturalness — the
  human's call, and it must be recorded in an ADR, not slipped in.
- Files: `backend/app/services/tts/` (one new provider module + a `TTS_PROVIDERS` entry), `.env.example`,
  `requirements.txt` **only if** a cloud/local library is chosen.

---

## Rules that constrain this cycle (carried over — do not re-litigate)

- **One item per human "go"**; small reviewable changes; plan before code; ask when unclear.
- **Functional fixes before UI polish**; cross-platform (Windows + Arch) from one requirements.txt.
- The four non-negotiables: raw words never edited/translated (**#1**) · the system never
  diagnoses (**#2**) · red flags are add-only, the local rule must survive total LLM outage
  (**#3**) · synthetic/consented data only, no auto-run live-LLM calls in dev (**#4**).
- Locked decisions stay locked unless the human reopens them explicitly: Teal Medical tokens
  (ADR-0043), background-assessed submit + 4–5 question floor (ADR-0042), M16 server-attached
  disclaimer (ADR-0044), OTP sender seam + dev-only `000000` bypass (ADR-0045), quota-aware
  provider switching (ADR-0041), bilingual `value_en`/`value_bn` (ADR-0033), and the S9 C1/C2
  human decisions. New real decisions in this cycle → new ADRs.
- Baseline this cycle starts from (**updated S30**): **318 tests pass, 1 skipped (opt-in `TTS_LIVE=1`) ·
  Alembic head 0012 · entry points `/` `/kiosk.html` `/medic/` `/doctor/` `/legacy/` · port 8001.**
  Never delete the DB.
- **New in S30 — do not regress TTS-1 (ADR-0051):** the split lives at the SINGLE entry point
  (`speak()`), covers BOTH providers, and must never migrate into the recording or display path.
- **Do not regress S1–S4 of the Requirement 3 cycle** (ADR-0048): the `[🎤 Speak][⌨ Type]` switch,
  auto-listen, the echo guard, and the 3-2-1 countdown/barge-in/flush are all live-tested PASS.
  In particular `ttsSpeaking()` — not `speechSynthesis.speaking` — must stay the echo-guard predicate
  (ADR-0049), or the mic reopens into the AI's own voice.

---

## The human's original requirements (verbatim — filled when findings arrive)

*(This section will hold the human's raw testing notes exactly as written, the same way
`context fixed problem 2.0.md` preserved the original 2.0 task text below its tracker.)*
