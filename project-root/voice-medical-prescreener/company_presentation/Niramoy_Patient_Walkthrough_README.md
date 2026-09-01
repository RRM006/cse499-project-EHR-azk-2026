# Niramoy Patient-Focused Walkthrough — What This Video Demonstrates

**File:** `Niramoy_Patient_Walkthrough.mp4` (~2 min 47 sec, 1600×900, narrated, subtitled)
**Companion files:** `Niramoy_Patient_Walkthrough.srt` (captions), `Niramoy_Patient_Walkthrough_Narration.md` (the script, to record in your own voice)

## What changed from the last version
The previous walkthrough split its time evenly across patient → medic → doctor. This one **makes the patient journey the main story** — about two-thirds of the runtime — and compresses "what happens after the patient" into a short closing sequence. If someone watches only the first half, they see the whole point of the product: a patient being pre-screened, hands-free, in their own language.

## The one sentence
**A patient speaks naturally → the AI structures the information → a medic verifies → a doctor decides → a structured EHR document comes out.** The video foregrounds the first arrow.

## The patient journey it shows (all real UI)
Every screen is the **actual running system** driven end-to-end on synthetic data — no mock-ups, no concept art:

1. **Sign in** — phone number, then a one-time code (which can also be spoken).
2. **Voice-first, hands-free** — the assistant asks a question out loud and the **microphone opens by itself**; the mic sits in its active listening state with nothing to tap. This is the slide that proves the system is *not* a touch kiosk.
3. **Answer naturally** — the patient replies in Banglish; voice is the primary path (typing is used here only to drive the same UI in a headless recording).
4. **Exact words preserved** — the system reads the answer back and stores it **verbatim**; the read-back panel shows the patient's own words unchanged (rule #1).
5. **Follow-up questions** — the assistant asks spoken follow-ups and the conversation thread builds up, one question at a time.
6. **Structured summary** — everything is organised into a clear summary the patient reviews (and can hear read aloud) before it's sent.
7. **Submit** — the patient confirms; risk and red flags are assessed **in the background, for the doctor** — the patient is never shown a diagnosis.

Then a brief tail: **medic** verifies the AI's summary against the raw words and adds vitals → **doctor** leads with safety (a Critical tier and a rule-based red flag on chest pain) → **Accept & Write to EHR** as an HL7 FHIR document. The diagnosis and prescription are always the doctor's own.

## What it proves for an engineering audience
1. **Voice-first, hands-free, for Bangladesh** — the intake is built around speaking, for elderly and low-literacy patients, in Bangla / Banglish / regional speech.
2. **Raw words are permanent** — verbatim capture and read-back, with cleaning and interpretation kept as separate later steps.
3. **The machine assists; people decide** — a medic verifies, a doctor decides, and the system never diagnoses. The red-flag safety rule runs independently of the AI.

## How it was made — honestly
- Browser speech recognition needs a live microphone, which a headless recording can't provide, so the patient's answers are **typed to drive the same real UI**, and the narration says so plainly. Every resulting screen — the read-back, the follow-up thread, the structured summary, the doctor's safety panel, the EHR output — is genuine system output.
- The follow-up questions and structured summary are shown through the **real UI components** (the app's own rendering code), populated from the case's stored data; the follow-up question is illustrative of the kind the system asks.
- Data is **synthetic/seeded** — no real patient information, no API keys, no `.env`, no source code on screen.

## Subtitles
Captions are **burned into the video** and also provided as a separate **`.srt`** sidecar, so they show in any player and can be re-used where an `.srt` is read separately.

## To present in your own voice
Open `Niramoy_Patient_Walkthrough_Narration.md` — the exact first-person script, with a timecode on every block matching the on-screen action.
