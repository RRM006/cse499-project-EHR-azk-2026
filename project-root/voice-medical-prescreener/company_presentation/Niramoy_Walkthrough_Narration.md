# Niramoy — Walkthrough Narration Script

**Use:** This is the exact voice-over in the walkthrough video. The delivered `.mp4` already has this narration and matching subtitles baked in. If you'd rather present in your own voice, read these lines over the muted video — each block is timed to the on-screen action, and the timecodes match the `.srt`.

**Voice:** first person, calm, confident — you're the engineer showing your own system. Don't rush; the pacing below has breathing room built in.

**Total runtime:** ~2 min 28 sec (16 segments).

---

## OPENING — Title card

**[0:00] (title card: "Niramoy")**
> This is Niramoy — a voice-first medical pre-screening system I designed and built for clinics in Bangladesh. Let me walk you through one real case, from start to finish.

---

## PART 1 — The Patient (voice-first intake)

**[0:11] (patient sign-in screen)**
> It starts with the patient. They sign in with just their phone number and a one-time code — no app to install, and no account to create.

**[0:19] (assistant asks first question, mic is open)**
> The assistant asks the first question out loud and shows it on screen, and the microphone opens by itself. I designed this to be hands-free, because many patients here are elderly or not comfortable with typing.

**[0:31] (patient's answer appears — Banglish text)**
> The patient answers naturally, in Bangla, Banglish, or a regional dialect. Voice is the primary path; I'll type here just to demonstrate, and either way their exact words are captured.

**[0:43] (raw transcript shown)**
> And those words are stored exactly as spoken, and never edited. That is the first rule of the whole system — cleaning and interpretation happen later, as separate steps.

---

## TRANSITION — Behind the scenes

**[0:53] (transition card)**
> Behind the scenes, the system now cleans those words, structures them, and asks follow-up questions to fill any gaps.

---

## PART 2 — The Medic (verification)

**[1:01] (medic triage queue)**
> Within seconds, the case appears on the medic's desk, in a queue ordered by urgency — not by who arrived first.

**[1:08] (case opened — conversation view)**
> Opening it, the medic sees the whole conversation: the patient's exact words, and the follow-up questions the system asked to complete the picture.

**[1:17] (structured 10-field summary)**
> From that speech, the AI has extracted a structured, ten-field clinical summary. The medic checks each field against the raw words, so a person always confirms what the machine understood.

**[1:28] (vitals section)**
> The medic also records vitals, like weight and blood pressure, before the case ever reaches the doctor.

---

## TRANSITION — Handover to the doctor

**[1:35] (transition card)**
> The medic forwards the case to the doctor — who always starts with safety.

---

## PART 3 — The Doctor (clinical decision) → EHR

**[1:40] (safety panel: Critical + red flag)**
> The doctor leads with safety: a Critical risk level, a red flag on chest pain, and a plain-language reason. That red flag is a rule that runs independently of the AI, so a real emergency cannot be missed even if the model gets it wrong.

**[1:56] (patient history timeline)**
> They also see the patient's history — earlier visits and prescriptions — for context.

**[2:02] (Accept & Write to EHR → FHIR output)**
> Then the doctor accepts the case into the record, and the system produces a structured E-H-R document — an HL7 FHIR bundle.

**[2:11] (prescription form — authored by the doctor)**
> And the prescription is the doctor's own — the diagnosis is theirs. The system never fills it in, and never diagnoses.

---

## CLOSING — Summary card

**[2:19] (closing card: Speak · Structure · Verify · Decide)**
> That is the core idea: the patient speaks, the AI structures, the medic verifies, and the doctor decides. Niramoy.

---

### One-line summary of the whole story
**Patient speaks naturally → AI structures the information → Medic verifies → Doctor makes the clinical decision → structured EHR output.**
