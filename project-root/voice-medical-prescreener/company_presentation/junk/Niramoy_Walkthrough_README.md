# Niramoy Walkthrough — What This Video Demonstrates

**File:** `Niramoy_Walkthrough.mp4` (~2 min 28 sec, 1600×900, narrated, subtitled)
**Companion files:** `Niramoy_Walkthrough.srt` (captions), `Niramoy_Walkthrough_Narration.md` (the script, if you want to record it in your own voice)

## The one sentence
**A patient speaks naturally → the AI structures the information → a medic verifies it → a doctor makes the clinical decision → a structured EHR document comes out the other end.**

## What you're watching (all real, no mock-ups)
Every screen in this video is the **actual running system** driven end-to-end on synthetic data — not concept art, not slides. It follows **one real case** through all three portals:

- **Patient portal (voice-first intake).** Phone + one-time-code sign-in, the assistant asking a question out loud with the mic opening on its own, the patient answering in Banglish, and the exact words being stored verbatim. This is the part that shows the system is designed to be **voice-first and hands-free**, for elderly and low-literacy patients — not a typing kiosk.
- **Medic portal (verification).** The case arriving in an urgency-ordered queue, the full conversation (raw words + the system's follow-up questions), the AI's 10-field structured summary being **checked against the raw words by a person**, and vitals being recorded.
- **Doctor portal (decision → EHR).** Safety first — a Critical risk level and a **rule-based red flag** that runs independently of the AI — then patient history, then accepting the case into the record as an **HL7 FHIR** document, and finally the **doctor's own prescription**. The system never diagnoses.

## The three ideas it's built to land
1. **Voice-first for Bangladesh.** The hard problem is Bangla / Banglish / regional speech and patients who can't or won't type. The whole intake is built around voice.
2. **The machine assists; people decide.** The AI cleans and structures; a medic verifies against the raw words; a doctor makes every clinical call. Nothing auto-diagnoses.
3. **Safety can't depend on the model.** The red-flag that catches a real emergency is a deterministic rule, so it fires even if the language model is wrong.

## How it was demonstrated safely (and honestly)
- Voice recognition is a browser microphone feature, so in a headless recording it can't literally hear a voice. Rather than fake it, the patient's answer is **typed to drive the same real UI**, and the narration says so plainly ("Voice is the primary path; I'll type here just to demonstrate"). Every resulting screen — transcript, extraction, triage, safety, EHR — is the genuine system output.
- Data is **synthetic/seeded** — no real patient information, no API keys, no `.env`, no source code on screen.

## How the subtitles work
Captions are **burned into the video** (always visible, nothing to enable) and also provided as a separate **`.srt`** sidecar file, so if you play the `.mp4` in a normal player you'll see them, and if you upload it somewhere that reads `.srt` you can use that instead.

## If you want to present it in your own voice
The video already has a clean narrated voice-over. If you'd prefer to narrate live or re-record, open `Niramoy_Walkthrough_Narration.md` — it's the exact script, in first person, with a timecode on every block matching the on-screen action.
