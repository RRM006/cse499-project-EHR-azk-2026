# portal_roles.md — What each portal is for, who owns which data, and what was deliberately NOT built

> Created **S37 (2026-08-13)**. This is the reference for the THREE entry points as *roles*:
> what each one does, why each feature belongs to that role and not another, and which table
> owns which fact. It exists because the portals were built feature-by-feature against numbered
> specs (KIOSK-n / MEDIC-n / DOCTOR-n) and had never been written down as a coherent division of
> labour — which is how the medic ended up able to record vitals only *after* handing the case over.
>
> Rules that constrain everything below: **rule #1** (raw words are never edited or re-rendered),
> **rule #2** (the system never diagnoses), **rule #3** (red flags surface, never reassure),
> **rule #4** (synthetic/consented data only in development).
> Decisions: **ADR-0058** (features + ownership), **ADR-0059** (the staff depth/motion layer).

---

## 1. The three roles in one line each

| Entry point | URL | Persona | The one question it answers |
|---|---|---|---|
| **Patient kiosk** | `/kiosk.html` | The patient, often elderly or non-technical, alone with a screen | "Tell us what is wrong, in your own words." |
| **Medic portal** | `/medic/` | Clinic triage staff at a desk, working a queue of waiting people | "Who do I handle next, and is this case fit to hand to a doctor?" |
| **Doctor portal** | `/doctor/` | The physician, one patient at a time, deciding | "What is going on with this person, and what do I do about it?" |

The handover chain is one-directional and is the visit `status`:

```
in_progress ──(patient submits)──▶ awaiting_review ──(medic forwards)──▶ awaiting_doctor
                                        │ MEDIC                                │ DOCTOR
                                        ▼                                      ▼
                                 verify · vitals · triage            review · prescribe
                                                                              │
                                                              ──(doctor reviews)──▶ reviewed / closed
```

---

## 2. MEDIC portal

### 2.1 Features that already existed (pre-S37)

| Feature | Endpoint(s) | Notes |
|---|---|---|
| Stub login (picks the seeded medic) | `GET /api/users?role=medic` | Auth is stubbed project-wide. |
| Case queue (`awaiting_review`), 15 s auto-refresh | `GET /api/dashboard?role=medic` | |
| Phone lookup across all statuses | `GET /api/dashboard?phone=` | |
| Verbatim raw panel, read-only | `GET /api/visits/{uuid}` | **Rule #1** — never editable, never translated. |
| Risk panel + staff tier override | `GET /risk`, `POST /risk/override` | MEDIC-3, audit-logged; a red-flag Critical cannot be downgraded. |
| C1 suggested condition, viewable + editable | `PATCH /profile/condition` | MEDIC-4, ADR-0036. Disclaimer re-attached server-side. |
| The 10 summary-field cards, editable | `PATCH /profile/fields/{key}` | Edits the DERIVED profile only; `source` becomes `human`. |
| Assign a doctor and forward | `POST /visits/{uuid}/assign` | |
| Post-referral summary + `.docx` download | `POST /documents/summary_report` | MEDIC-6/7; report regenerated fresh at download. |

### 2.2 Features ADDED in S37

| # | Feature | Why a medic needs it | Why it is MEDIC, not doctor/patient | Data |
|---|---|---|---|---|
| **M-1** | **Triage-ordered queue** — worst tier first, then longest wait | The queue was newest-first, so a Critical patient waiting 40 min sat *below* a Low-risk one who had just submitted | Choosing who is seen next IS the triage role. The doctor's queue is a short assigned-to-me list; the patient never sees a queue | Existing `risk_assessments.tier` + `visits.submitted_at` |
| **M-2** | **Wait time, red-flag chip and intake meter on every row** | Decide whether to open a case without opening it | Same as M-1; the doctor receives cases one at a time, already triaged | Derived; `empty_field_keys` shares M9's `field_has_text` |
| **M-3** | **Floor-load strip** (waiting / critical / high / not assessed / longest wait) | Answers "how bad is the floor right now" — the thing a triage desk is accountable for | Clinic-wide load is a desk concern; a doctor sees their own list, a patient sees none | Derived from the SAME rows the queue lists |
| **M-4** | **Intake & Vitals card, BEFORE the referral** | The medic could previously record weight/BP/identity **only after forwarding**, so the doctor got every case with no vitals | Vitals capture is the classic medic/nurse task. Doctor keeps its own DOCTOR-3 card — same row, same endpoint, later moment | `patients` (unchanged), `PATCH /patients/{id}/vitals` |
| **M-5** | **Handover check** (advisory) | Says what the doctor is about to be missing, while the medic can still fix it | It is about the quality of the *hand-off*, which only the sender can improve | `GET /visits/{uuid}/handoff` — read-only |
| **M-6** | **Referral attribution** | `audit_log` recorded who RECEIVED a case, never who sent it | Accountability for the medic's own action | `AssignRequest.editor_id` → existing `audit_log.actor_id` |

⚠ **M-5 is advisory and can never block a forward.** A medic must be able to push a Critical patient
to a doctor immediately, incomplete paperwork and all (ADR-0058 d). Two tests pin that.

### 2.3 Medic use cases

1. **Work the floor.** Open `/medic/`, read the load strip, take the top row — it is the most urgent
   longest-waiting patient, not the newest.
2. **Spot an unassessed case.** Unassessed sorts *between* High and Medium, so it cannot hide.
3. **Verify the AI's reading.** Compare the 10 fields against the verbatim panel; correct what is
   wrong (the edit becomes `human` and M8 will never overwrite it).
4. **Record vitals and confirm identity** before the doctor ever sees the case.
5. **Escalate.** Override the tier with a reason where the model got it wrong (audit-logged).
6. **Hand over.** Read the handover check, fix what is quick, forward to a named doctor, download the
   summary `.docx`.

---

## 3. DOCTOR portal

### 3.1 Features that already existed (pre-S37)

| Feature | Endpoint(s) | Notes |
|---|---|---|
| Stub login (choose a seeded doctor) | `GET /api/users?role=doctor` | |
| Assigned queue (`awaiting_doctor`, filtered to me) | `GET /api/dashboard?role=doctor&doctor_id=` | |
| Phone lookup | `GET /api/dashboard?phone=` | |
| Verbatim raw panel | `GET /api/visits/{uuid}` | **Rule #1.** |
| Safety panel: tier, red flags, XAI reason | `GET /risk` | DOCTOR-7 — the safety story is shown first. |
| Patient details + vitals edit | `PATCH /patients/{id}/vitals` | DOCTOR-3. |
| C1 suggested condition (shared card) | `PATCH /profile/condition` | Never flows into the prescription Diagnosis. |
| 10 field cards, editable | `PATCH /profile/fields/{key}` | |
| Review: Accept, or Override to Low-Risk, + notes | `POST /visits/{uuid}/review` | M14. |
| Prescription form → saved row + `.docx` | `GET/POST …/prescription` | DOCTOR-4/5/6. **Diagnosis is doctor-authored and never AI-filled.** |
| AI drug-information assistant (M16) | `POST …/assistant/drug-info` | Server-attached disclaimer, informational only. |
| Print-friendly case view | CSS only | DOCTOR-7. |

### 3.2 Features ADDED in S37

| # | Feature | Why a doctor needs it | Why it is DOCTOR, not medic/patient | Data |
|---|---|---|---|---|
| **D-1** | **Patient timeline** — prior visits with date, complaint, tier, red flags, treating doctor | The portal showed exactly one visit. "Third time this month with the same complaint?" was unanswerable | Comparing encounters is a clinical judgement; the medic works the case in front of them, the kiosk ends at submission | `GET /patients/{id}/history` — read-only |
| **D-2** | **Prior prescriptions**, from every doctor, with `.docx` links | `prescriptions` was a **write-only table** — a repeat medication was undetectable from inside the portal | Prescribing is doctor-only; a medic never issues one | Same endpoint; reads `prescriptions` + `documents` |
| **D-3** | **Completed-consultations scope** (Queue / Completed) | Reviewing a case made it VANISH — the queue lists only `awaiting_doctor`, so the case had no route back except a phone search | A completed-consultation list is personal to one doctor | `GET /api/dashboard?role=doctor&scope=recent&doctor_id=` |
| **D-4** | **Reviewed cases stay open and change state** | Writing the prescription AFTER accepting is the normal order; the old flow dropped the case first | — | Existing `visits.status` |
| **D-5** | **Review controls hide once reviewed** | `POST /review` 409s on a reviewed visit, so offering the button was offering an error | — | Frontend only |

⚠ **D-1 carries no transcript.** A prior visit is opened via `GET /api/visits/{uuid}` and read from
the one immutable copy — a summarised history row would be a second, lossy rendering of the
patient's words (rule #1). ⚠ **D-1 interprets nothing**: two visits with the same complaint are two
rows with two dates (rule #2).

### 3.3 Doctor use cases

1. **Read the safety story first** — tier, red flags, XAI reason, before anything else.
2. **Check the history** before deciding: has this complaint recurred, what was tried, what was
   prescribed, by whom.
3. **Read the patient's own words** in the verbatim panel and correct any field the AI misread.
4. **Look a medicine up** (M16) without leaving the case; the reply always carries its disclaimer.
5. **Decide** — Accept & Write to EHR, or Override to Low-Risk, with notes.
6. **Prescribe** — author the Diagnosis themselves, generate the `.docx`, and find it again later
   under Completed.

---

## 4. How the roles connect

**MEDIC ↔ PATIENT.** The medic never speaks to the kiosk. They receive the patient's `visit` at
`awaiting_review` and read the raw transcript the patient produced. The only patient-owned record a
medic writes is the `patients` row (name/age/sex/weight/BP) — never the transcript, and the derived
`summary_fields` only as a labelled human correction.

**MEDIC ↔ DOCTOR.** One hand-off: `POST /visits/{uuid}/assign` sets `assigned_doctor_id` and moves
the status to `awaiting_doctor`. Since S37 that action also records the sending medic in
`audit_log.actor_id`. Everything the medic edited is visible to the doctor because both read the
SAME `case_profiles` row — there is no copy and no message.

**DOCTOR ↔ PATIENT.** The doctor reads the patient's words and writes the clinical outcome
(`doctor_reviews`, `prescriptions`). The patient never sees the doctor's portal; the prescription
`.docx` is the artefact that crosses back.

**DOCTOR ↔ MEDIC.** The doctor sees the medic's work as data, not as a report: `source: 'human'`
fields, a `model_provider: 'human'` risk row, vitals on the patient. The doctor can edit the same
fields; the medic is not notified (there is no back-channel by design — the status flow is
one-directional).

**Deliberately NOT shared.** The kiosk never sees a queue, a tier, a red flag or a suggested
condition. The medic never sees prescriptions, the drug assistant, or a doctor's completed list.
The doctor never sees the triage load strip or the handover check.

---

## 5. Data ownership matrix (verified S37 — `models.py` and `migrations/` untouched, Alembic head 0012)

| Fact | Owning table | Written by | Read by | Never duplicated because |
|---|---|---|---|---|
| Patient identity (name, sex, birth year) | `patients` | Kiosk auto-fill (empty fields only) · medic · doctor | all three | One row; staff values are final and the AI only fills EMPTY fields |
| Phone (`external_ref`) | `patients` | Kiosk lookup | staff | Unique per clinic; the OTP flow keys on it |
| Vitals (weight, BP) | `patients` | **medic (pre-handoff)** and doctor | staff | Same row, same `PATCH /patients/{id}/vitals`, two moments of one workflow |
| **Raw words** | `utterances.raw_text` | Kiosk only, write-once | staff (read-only) | **Rule #1.** Nothing else stores or re-renders them |
| Corrected text | `utterances.corrected_text` | Correction service | staff | A SEPARATE column; raw is untouched |
| The 10 summary fields | `case_profiles.entities.summary_fields` | M3/M8 (`ai`) · staff edits (`human`) | staff | One JSON blob; M8 never overwrites `human` |
| Suggested condition (C1) | `case_profiles.entities.suggested_condition` | M10C · staff edit | staff | Never copied into the prescription Diagnosis (rule #2) |
| Risk tier / red flags | `risk_assessments` (append-only) | M10 · staff override row | staff | Latest row wins; history preserved |
| Visit state + assignment | `visits` | Kiosk submit · medic assign · doctor review | all | The one workflow state machine |
| Doctor decision | `doctor_reviews` (append-only) | doctor | doctor | — |
| Prescription | `prescriptions` (+ linked `documents`) | doctor | doctor (via D-1/D-2) | The payload JSON is the source; the history shows a NAME PREVIEW only |
| Who did what | `audit_log` | every staff write | — | Loose entity link; no per-table FK |
| **Wait time** | *(derived)* | nobody | medic, doctor | Computed from `submitted_at` per request |
| **Intake completeness** | *(derived)* | nobody | medic | Computed from `summary_fields` per request |
| **Handover readiness** | *(derived)* | nobody | medic | Composed from requirements + risk + vitals per request |
| **Queue load figures** | *(derived)* | nobody | medic | Computed from the same rows the queue lists |
| **Patient history** | *(derived)* | nobody | doctor | Assembled from visits/prescriptions/documents per request |

Enforced by two behavioural tests: calling every new S37 endpoint creates **zero** rows across six
tables, and renaming a patient or a doctor changes the queue **immediately** (nothing cached an
identity it does not own).

---

## 6. Considered and deliberately NOT implemented (with the reason)

| Idea | Why not |
|---|---|
| **Medic "my completed referrals" list** | Nothing records WHICH medic forwarded a case, so the list would show every medic's work as one person's, or need a new column to invent the attribution. `scope=recent&role=medic` returns **400 with the reason**. The useful half — attribution going forward — shipped as M-6 using an existing column. |
| **Per-field "verified" checkbox for the medic** | A real gap (a medic cannot record "I read this and it is correct" without editing the value), but it needs new per-field state and new UI vocabulary. `source == 'human'` already gives the weaker `fields_verified` signal. Deferred rather than half-built. |
| **Blocking the forward on the handover check** | Unsafe. A Critical patient must reach a doctor with incomplete paperwork rather than wait for it. |
| **A numeric triage score** | Would be a number nobody could verify, and collides with decision C2 (no per-case percentages are generated or stored). |
| **A medic messaging/notes channel back from the doctor** | The status flow is deliberately one-directional; a back-channel needs its own state, notification model and read/unread semantics. Not in scope, and no evidence yet that the clinic needs it. |
| **Doctor-side follow-up scheduling / recall list** | The prescription already carries a follow-up date. A recall queue would need a new owner (who acts on it?) and a new table. Genuinely out of scope for S37. |
| **Duplicating vitals editing away from the doctor** | Both roles legitimately touch the same `patients` row at different moments. Removing one would break a real workflow; both use the same endpoint, so there is no second source of truth. |
| **Copying patient identity into a medic-owned record** | Explicitly forbidden by ADR-0058 h. The queue resolves names per request. |
| **Showing prior raw transcripts inside the timeline** | Rule #1 — a summarised history row would be a second rendering of the patient's words. The doctor opens the prior visit instead. |
| **Trend lines / "recurring condition" detection on the timeline** | Rule #2. Two visits with the same complaint are two rows with two dates; what that means is the doctor's call. |
| **3D objects / WebGL in the portals** | No discrete GPU on either dev machine; cost with no clinical benefit (ADR-0059). |
| **Animating the queue's reorder (FLIP)** | Rows would move under a medic's cursor as they reach for one. |
