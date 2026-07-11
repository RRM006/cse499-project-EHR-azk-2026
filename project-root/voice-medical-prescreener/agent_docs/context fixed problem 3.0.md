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
> **Status: 🕐 EMPTY — waiting for the human's manual-testing findings. No items yet, nothing to
> build from this file yet.** (The faculty's quantized-model requirements are NOT part of this
> cycle either — they live in `agent_docs/faculty_future_features.md`, a separate research track.)
>
> **Legend (same as 2.0):** ✅ done · ⏳ in progress · ⬜ not started · 👉 the next step

---

## 📥 RAW FINDINGS INBOX (human: paste here — any format, no polish needed)

> Tip from the 2.0 cycle: per finding, one line each for **where** (which portal/screen),
> **what happened / what you expected**, and **how bad** (blocker / annoying / nice-to-have)
> makes the triage fast — but plain unstructured notes are fine too.

*(nothing yet)*

---

## Progress at a glance

*(built after the first findings are triaged — will mirror 2.0's STRUCT/P1/P2/P3 style:
cross-cutting items first, then per-portal priorities, functional before polish)*

## Checklist (maps to the findings below)

*(no items yet)*

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
- Baseline this cycle starts from: **192 tests pass · Alembic head 0012 · entry points
  `/` `/kiosk.html` `/medic/` `/doctor/` `/legacy/` · port 8001.** Never delete the DB.

---

## The human's original requirements (verbatim — filled when findings arrive)

*(This section will hold the human's raw testing notes exactly as written, the same way
`context fixed problem 2.0.md` preserved the original 2.0 task text below its tracker.)*
