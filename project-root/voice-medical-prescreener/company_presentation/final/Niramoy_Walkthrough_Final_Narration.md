# Niramoy — Walkthrough Video: final narration

Runtime **2:55** · 16 scenes · 440 spoken words · voice: Kokoro neural TTS (local, offline), voice `am_michael`

Captions are the same sentences, verbatim — only acronym spelling, hyphenation and capitalisation differ (`python narration.py` proves it word for word).

| Scene | In | Out | On screen | Narration |
|---|---|---|---|---|
| S1 | 0:00 | 0:07 | Title card | This is Niramoy, a voice first medical pre-screening system I built for clinics in Bangladesh. |
| S2 | 0:06 | 0:15 | Patient Portal — sign in (live) | The patient starts here. No app and no account. Just a mobile number, typed, or spoken digit by digit into the microphone. |
| S3 | 0:15 | 0:22 | Patient Portal — one-time code (live) | A one time code signs them in. It is hashed, single use, and it expires in five minutes. |
| S4 | 0:21 | 0:34 | Patient Portal — voice-first, hands-free (live) | Now the core of the system. The assistant asks its question aloud and on screen, and then the microphone opens by itself. Nothing to tap. The portal says so in its own words. |
| S5 | 0:34 | 0:44 | Patient Portal — Bangla / English (live) | The whole portal runs in Bangla or English, and the patient can answer in Bangla, in Banglish, or in their own regional way of speaking. |
| S6 | 0:43 | 0:55 | Patient Portal — typing fallback chosen (live) | For this recording I am using the typing fallback, because this capture environment has no live microphone. The same flow accepts voice in the running application. |
| S7 | 0:55 | 1:05 | Patient Portal — answering (live) | Everything else is live. The assistant works through its questions, and every answer goes into exactly the same pipeline the microphone uses. |
| S8 | 1:04 | 1:15 | Patient Portal — verbatim capture (live) | And whatever the patient gives, it is stored exactly as they said it. Never edited, never cleaned. That is the first rule this whole system is built on. |
| S8b | 1:14 | 1:26 | The patient's own raw-transcript document | And at the end of the visit, the patient leaves with their own copy. The whole conversation, exactly as it was captured, generated automatically and handed back to them. |
| S9 | 1:26 | 1:36 | Medic Portal — triage queue | When a patient submits, the case moves to the medic's queue, ordered by urgency rather than arrival. This one is critical, and it carries a red flag. |
| S10 | 1:35 | 1:52 | Medic Portal — the patient's words + the 10 extracted fields | Here is that patient's own conversation. The follow up questions the system asked, in Bangla and English, and the answers, word for word. Underneath, the A I's structured reading of the same conversation, in ten clinical fields. |
| S11 | 1:51 | 2:00 | Medic Portal — verify, vitals, forward | The medic checks the machine's reading against the patient's own words, records the vitals, and forwards the case to a named doctor. |
| S12 | 2:00 | 2:16 | Doctor Portal — safety, red flag, tier | The doctor's case opens with safety. A rule based check found chest pain in the patient's own words and forced the tier to critical. That rule is local and deterministic. The model can raise concern. It can never suppress the rule. |
| S13 | 2:15 | 2:29 | Doctor Portal — XAI reason, prescription | Beside it sits the stored explainable A I reason. Then the doctor writes the diagnosis themselves. The A I's suggestion never enters it. The system narrows. The clinician decides. |
| S14 | 2:29 | 2:47 | Accept & Write to EHR → FHIR R4 bundle | Accepting the case writes the encounter as an H L seven FHIR R four document bundle, with the patient's verbatim words carried through, and the risk exported as a risk assessment rather than a diagnosis. The same record renders as a P D F a person can read. |
| S15 | 2:47 | 2:55 | Closing card | The patient speaks. The system structures. The medic verifies. The doctor decides. And it becomes a medical record. |

## The narration, as one read

> This is Niramoy, a voice first medical pre-screening system I built for clinics in Bangladesh.

> The patient starts here. No app and no account. Just a mobile number, typed, or spoken digit by digit into the microphone.

> A one time code signs them in. It is hashed, single use, and it expires in five minutes.

> Now the core of the system. The assistant asks its question aloud and on screen, and then the microphone opens by itself. Nothing to tap. The portal says so in its own words.

> The whole portal runs in Bangla or English, and the patient can answer in Bangla, in Banglish, or in their own regional way of speaking.

> For this recording I am using the typing fallback, because this capture environment has no live microphone. The same flow accepts voice in the running application.

> Everything else is live. The assistant works through its questions, and every answer goes into exactly the same pipeline the microphone uses.

> And whatever the patient gives, it is stored exactly as they said it. Never edited, never cleaned. That is the first rule this whole system is built on.

> And at the end of the visit, the patient leaves with their own copy. The whole conversation, exactly as it was captured, generated automatically and handed back to them.

> When a patient submits, the case moves to the medic's queue, ordered by urgency rather than arrival. This one is critical, and it carries a red flag.

> Here is that patient's own conversation. The follow up questions the system asked, in Bangla and English, and the answers, word for word. Underneath, the A I's structured reading of the same conversation, in ten clinical fields.

> The medic checks the machine's reading against the patient's own words, records the vitals, and forwards the case to a named doctor.

> The doctor's case opens with safety. A rule based check found chest pain in the patient's own words and forced the tier to critical. That rule is local and deterministic. The model can raise concern. It can never suppress the rule.

> Beside it sits the stored explainable A I reason. Then the doctor writes the diagnosis themselves. The A I's suggestion never enters it. The system narrows. The clinician decides.

> Accepting the case writes the encounter as an H L seven FHIR R four document bundle, with the patient's verbatim words carried through, and the risk exported as a risk assessment rather than a diagnosis. The same record renders as a P D F a person can read.

> The patient speaks. The system structures. The medic verifies. The doctor decides. And it becomes a medical record.
