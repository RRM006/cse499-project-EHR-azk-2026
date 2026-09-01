# Niramoy — Likely Interview Questions & Answers

> Grounded only in what the project actually contains. **Short answer** = what to say first (confident, ~2 sentences). **If they push** = the deeper follow-up. If you don't know something, the honest move is "I haven't measured/built that yet — here's how I'd approach it." That reads as senior, not weak.

---

## 1. Project understanding

**Q. In one sentence, what is Niramoy?**
- **Short:** A voice-first medical pre-screening system where a patient speaks their symptoms in Bangla or Banglish before the visit, and the doctor gets a structured, safety-checked summary.
- **If they push:** It's a 15-module pipeline — speech-to-text, cleaning, extraction, follow-up questioning, risk assessment with red flags and an explanation, then a doctor dashboard and EHR export. It assists the doctor and never diagnoses.

**Q. Who's the user, and why voice?**
- **Short:** The patient is often elderly, low-literacy, or anxious, and speaks Bangla/Banglish/dialect. Typing a medical history in Bangla is a real barrier, so voice is the inclusive default.
- **If they push:** Typing is always available as a fallback through the same pipeline — but leading with voice is what lets the people who most need help actually use it.

**Q. What problem does it really solve?**
- **Short:** Consultations are two–three minutes; history-taking gets compressed and details are missed. Niramoy front-loads a structured history so the doctor starts informed.

---

## 2. Architecture

**Q. Walk me through the architecture.**
- **Short:** Browser portals (HTML/JS) → FastAPI REST → a service layer with one file per module → a repository → SQLite via SQLAlchemy with Alembic migrations. One swappable OpenAI-compatible client handles all AI tasks.
- **If they push:** The `visit` is the aggregate root; every pipeline output is a child table on it. New module *runs* are just a new `module_code` in `module_events` — no schema change. Evolving structured data lives in JSON columns until a real query needs a column. That's the "extend without rewriting" design.

**Q. Why FastAPI?**
- **Short:** Typed, clean REST now, and its async model suits the future streaming STT over WebSocket. Uvicorn runs it with one command, cross-platform.

**Q. Monolith or microservices?**
- **Short:** A modular monolith — one backend, one DB, clean module boundaries in the service layer. For a single-clinic deployment that's the right call; the `clinic_id` seam and config-driven DB URL make scaling out additive later.

---

## 3. AI / ML

**Q. Where exactly is the AI, and where is it not?**
- **Short:** LLM does correction (M2), extraction (M3), summary (M4), follow-ups (M7), answer-merge (M8), the risk tier (M10), the explanation (M11), the report prose (M12), and the drug assistant (M16). STT (M1), completeness (M9), and the red-flag rule are **local, no AI.**
- **If they push:** That split is deliberate — the safety-critical red-flag check must not depend on a model's mood, and completeness is a deterministic score, so both are rules.

**Q. Which models, and how do you handle rate limits?**
- **Short:** All providers are OpenAI-compatible, so one client swaps between Gemini Flash / Flash-Lite, Groq, Cerebras, and OpenRouter. Redundancy multiplies across three dimensions — providers × keys × models — and a 429 cools down only that one path, temporarily.
- **If they push:** Order is every model of key 1, then key 2, then the next provider. It came from a real outage: the night before a demo, one model was retired upstream and another was rate-limited, so I re-architected the fallback so a single dead provider can't stop an intake.

**Q. How do you keep the model from hallucinating symptoms?**
- **Short:** Two ways. The raw transcript is immutable and always shown, so the doctor can check any extracted field against what was actually said; and the extraction is constrained to ten fixed fields with a strict prompt that says not to add or infer.
- **If they push:** Extracted fields are labelled `ai`; a human edit relabels them `human` and the AI merge never overwrites a human value. The system also never emits a diagnosis or a numeric score.

**Q. Did you train any models?**
- **Short:** No — this version uses hosted LLMs behind a swappable client, and browser speech APIs for STT/TTS. Training a local quantized model is the explicit next phase; the whole design exists so that swap is a config change.
- **If they push (honest):** So there's no fine-tuning or WER number from me yet. The plan is to fine-tune/quantize a Bangla clinical speech + summary model and evaluate it against the current cloud pipeline on the same synthetic set.

---

## 4. Backend

**Q. How is the backend organised?**
- **Short:** `api/` has thin routers; `services/` has one file per module holding the logic; `db/` has the models and repository; `core/` has config and the provider registry. Routers call services, services call the LLM client and the repository.
- **If they push:** State-changing calls also write an `audit_log` row and a `module_events` row (provider + latency), so accountability and the free-tier strategy are observable without extra endpoints.

**Q. How does a follow-up request work server-side?**
- **Short:** `POST /followup/answer` runs M8 merge → M9 completeness → M7 next question and returns the next question **in the same response**, so the voice frontend needs no second round-trip. The loop is bounded (min ~4, max ~5, threshold ~0.7).

**Q. How are documents generated?**
- **Short:** The DB is the source of truth; documents are regenerable renderings. Word via python-docx, PDF via fpdf2 + HarfBuzz for correct Bangla shaping, and an HL7 FHIR R4 bundle for the EHR write.

---

## 5. Frontend

**Q. Why plain HTML/JS and not React?**
- **Short:** Fastest path to a reliable kiosk for non-technical users; the device is just a browser with a mic. React was deferred as an explicit decision, not an oversight.
- **If they push:** The three portals share a design system and helper scripts (`shared.js`, `staff.js`, `tts.js`). It's testable via static-asset assertions, and there's no build step to break the "one requirements.txt + a venv" promise.

**Q. How does the voice interaction actually work in the browser?**
- **Short:** `webkitSpeechRecognition` with `continuous` + `interimResults` on `bn-BD`. After the question's TTS ends, an echo guard opens the mic; interim results feed a silence timer that triggers a visible 3-2-1 confirmation, and any resumed speech cancels it.
- **If they push:** TTS is server-side (edge-tts neural Bangla, espeak fallback), because Windows ships no Bengali voice. On-screen text is always the mandatory fallback. Voice and typing hit the same endpoint, differing only by a `source` flag.

**Q. What happens if the mic fails?**
- **Short:** It falls back to a typing box that runs the identical pipeline — the demo you saw actually shows that graceful degradation when no mic is present.

---

## 6. Database

**Q. Why SQLite? Doesn't that limit you?**
- **Short:** For a single-clinic capstone it's zero-setup and perfectly adequate; the DB URL is config-driven, so moving to Postgres is one line and no code change. Concurrency and multi-writer are the reasons you'd switch, not the schema.
- **If they push:** The schema is written portably (JSON and timestamps map cleanly), and a `clinic_id` tenancy seam is on every top-level row so multi-clinic is additive.

**Q. How does the schema avoid churn as features grow?**
- **Short:** Everything hangs off the `visit` aggregate root, append-only for clinical/audit data, and evolving shapes live in JSON columns. A new module is a new `module_code` value — no migration. There have been 14 migrations for 18 tables — most feature work added no schema at all.

**Q. How do you store the patient's identity safely?**
- **Short:** Minimal PII — year of birth, not full DOB; phone as the key; explicit consent flag. Identity is keyed by phone so a returning patient links across visits.
- **If they push:** That created a subtle bug — a name entered once showed on later visits. The fix surfaces the name's **origin** from the audit log and reports `unknown` rather than guessing.

---

## 7. APIs

**Q. How is the API designed?**
- **Short:** Resource-oriented REST under `/api`, mostly nested under `visits`, so the whole patient journey reads as operations on one growing object. There's a public `GET /api/config` for kiosk timings and a `GET /health`.
- **If they push:** Writes that trigger a pipeline stage return the updated visit slice, so the frontend avoids a second call. Old flat endpoints were kept as aliases during migration — no breaking change.

**Q. Any third-party APIs?**
- **Short:** The LLM providers (OpenAI-compatible), a free no-key DuckDuckGo search for the drug assistant, and TextBee for real SMS OTP. Each sits behind a swappable interface.

---

## 8. Security & privacy

**Q. Is patient data secure?**
- **Short:** Honestly, this is a research prototype, so I use synthetic/consented data only. OTP is real — hashed, expiring, single-use — and every action is audit-logged. But staff auth is stubbed and there's no encryption at rest yet; both are on the roadmap.
- **If they push:** The real privacy issue today is that browser STT sends audio to Google and edge-TTS sends the question to Microsoft, and free LLM tiers may train on inputs. That's precisely why the top future priority is on-device models — it removes those data paths entirely.

**Q. How would you make it production-ready for real patients?**
- **Short:** Real authentication and role-based access, encryption at rest and in transit, a no-training or local LLM, on-device STT/TTS, Postgres, and a formal audit/compliance pass.

---

## 9. Scalability

**Q. How does this scale to many clinics?**
- **Short:** The `clinic_id` seam is on every top-level row, so multi-tenant is adding rows, not reshaping tables. Move the DB URL to Postgres, put it in a container, and the app runs unchanged.
- **If they push:** The stateless REST layer scales horizontally; the bounded follow-up loop caps per-visit LLM calls; and `module_events` gives per-module latency/provider metrics to find bottlenecks.

**Q. What's the bottleneck?**
- **Short:** The LLM calls and their free-tier quotas — which is exactly what the provider×key×model fallback and the future local model address.

---

## 10. Testing & debugging

**Q. How did you test this?**
- **Short:** Around 1,196 pytest tests, all offline, covering the follow-up loop, extraction, triage, risk and red-flag override, OTP, TTS, migrations, the multi-key fallback, and raw-immutability. The immutability rule is pinned by its own test.
- **If they push:** UI behaviour is covered by backend and static-asset tests; the honest gap is that browser *appearance* and live mic accuracy need a human run, which I do and record.

**Q. Tell me about a hard bug.**
- **Short:** A medic "Edit" button did nothing. It wasn't the handler or the API — a CSS transform under a `perspective` rescaled the card on press, so `mousedown` and `mouseup` hit different elements and the click never fired. I fixed it by carrying depth in the shadow instead of a transform.
- **If they push:** The lesson: a programmatic `.click()` can't detect a hit-target defect — it skips hit-testing — so anything about whether a control can be *pressed* has to be driven with a real mouse. I added a test that reproduces it with real mouse events.

---

## 11. Difficult problems (have 2–3 ready)

**Q. What was the hardest engineering problem?**
- **Short:** Three good ones — (1) the provider outage that forced the three-dimensional LLM fallback; (2) making the voice loop hands-free without ever clipping a patient's words; (3) rendering Bangla correctly in the PDF.
- **The Bangla PDF one:** ReportLab can't shape Bengali conjuncts, so words came out as disconnected glyphs in the wrong order — which would break the "never change the patient's words" rule in the one export a human reads. I switched to fpdf2 delegating shaping to HarfBuzz, and made the renderer **refuse** rather than emit broken Bangla. A test checks every drawn character against the font.
- **The date bug:** prescriptions written after midnight Dhaka got dated the previous day, because the server stamped the UTC date. Fixed with a fixed UTC+06:00 offset (Windows has no tz DB; Bangladesh has no DST), and a category-based date policy — historical timestamps untouched, a prescription must be dated today.

**Q. Where did you have to say "no" to a feature?**
- **Short:** A numeric triage score, and blocking a forward on an incomplete handover. A score would be false precision nobody could justify; and a Critical patient must reach a doctor even with incomplete paperwork, so the handover check is advisory and can never block.

---

## 12. Future improvements

**Q. What's next?**
- **Short:** On-device: a local quantized summary model and local STT/TTS, so no patient data leaves the machine. Then finish the fully hands-free loop, add real auth + Postgres + encryption, and run a formal accuracy evaluation.
- **If they push:** The on-device swap is cheap *because* every AI call already goes through one OpenAI-compatible client and STT sits behind a provider seam — that design decision was made specifically to enable this.

**Q. If you had two more weeks?**
- **Short:** I'd wire up the S5 voice-robustness (no-speech re-prompt, permission recovery, hard cap) and run a measured WER/precision-recall pass on a real Bangla/Banglish sample — the numbers I'm deliberately not claiming yet.

---

## 13. Curveballs & ownership

**Q. How much of this did you build vs. AI coding tools?**
- **Short:** I used AI coding assistance to move fast, and I directed and own the system. I made the architecture and technology decisions, set the non-negotiable rules, debugged the real defects, and curated the tests and decision records. I can open any file and explain what it does and why.
- **If they push:** Point to specifics — the three-dimensional fallback design, the raw-immutability invariant, the Bangla PDF refusal, the timezone fix, the hit-target bug. Those are judgment calls and diagnoses, not generated boilerplate.

**Q. What would you do differently?**
- **Short:** Measure earlier — I'd have set up the WER/precision harness at the start so I had numbers throughout. And I'd have put real auth in sooner rather than carrying a stub.

**Q. Why should we hire you off this?**
- **Short:** Because I took a genuinely hard, real-world problem — Bangla voice in a clinic — designed a system around honest constraints, made defensible engineering trade-offs, debugged the ugly bugs, and I can explain every decision. I also know exactly what *isn't* done, which is how I'd work on your team.
