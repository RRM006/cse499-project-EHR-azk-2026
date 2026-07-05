"""Database models.

CONSTITUTION RULE #1 — the raw transcript is permanent and is never modified.
``raw_text`` is written once at insert time. The correction lives in a SEPARATE
column (``corrected_text``) and never overwrites the raw words.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class Clinic(Base):
    """Tenant root (architecture.md principle 1). One row now; multi-clinic is additive later.

    ``address``/``logo_path`` feed the prescription letterhead (DOCTOR-4, rev 0010) —
    stored here so every prescription reuses them without re-entry.
    """

    __tablename__ = "clinics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class User(Base):
    """Staff accounts. Auth is stubbed for now (architecture.md assumption).

    Roles: 'doctor' | 'medic' | 'desk' | 'admin'. 'medic' is the triage role from the
    mockup reconciliation (ADR-0030) — verifies extracted fields and assigns a doctor.
    """

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('doctor','medic','desk','admin')", name="ck_users_role"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    # Doctor letterhead fields for the prescription module (DOCTOR-4, rev 0010).
    qualification: Mapped[str | None] = mapped_column(String(255), nullable=True)
    registration_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    specialization: Mapped[str | None] = mapped_column(String(255), nullable=True)
    signature_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Patient(Base):
    """The person being screened. Minimal PII; consent explicit (rule #4).

    ``external_ref`` holds the normalized phone number ("+8801...") used by the kiosk
    phone-lookup (ADR-0030) — unique per clinic. Hashing can replace it later without
    a schema change.
    """

    __tablename__ = "patients"
    __table_args__ = (
        UniqueConstraint("clinic_id", "external_ref", name="uq_patients_clinic_external_ref"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.id"), nullable=False)
    external_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sex: Mapped[str | None] = mapped_column(String(16), nullable=True)
    birth_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Vitals for the staff patient-details views (DOCTOR-3 / MEDIC-6, rev 0010);
    # weight is medic-editable, bp is a free-form reading like "120/80".
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    bp: Mapped[str | None] = mapped_column(String(32), nullable=True)
    consent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Visit(Base):
    """ONE pre-screening encounter — the aggregate root everything hangs off (principle 2).

    Status flow (ADR-0030): in_progress → awaiting_review (patient submitted; medic queue)
    → awaiting_doctor (medic forwarded; doctor queue) → reviewed → closed.
    ``assigned_doctor_id`` is set by the medic's "Submit & Forward".
    """

    __tablename__ = "visits"
    __table_args__ = (
        CheckConstraint(
            "status IN ('in_progress','awaiting_review','awaiting_doctor','reviewed','closed')",
            name="ck_visits_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, default=_new_uuid)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.id"), nullable=False)
    patient_id: Mapped[int | None] = mapped_column(ForeignKey("patients.id"), nullable=True)
    assigned_doctor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="in_progress", server_default="in_progress"
    )
    language: Mapped[str] = mapped_column(
        String(8), nullable=False, default="bn-BD", server_default="bn-BD"
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CaseProfile(Base):
    """M3/M4/M6/M8/M9 working state for one visit — derived, mutable (the immutable
    source stays in utterances; module_events + utterances reconstruct history).

    ``entities`` holds the extraction JSON including the Pydantic-enforced
    ``summary_fields`` 10-key shape (ADR-0030); ``gaps`` is the M6 present-vs-missing
    checklist. JSON so the shape can evolve without migrations (principle 3).
    """

    __tablename__ = "case_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    visit_id: Mapped[int] = mapped_column(ForeignKey("visits.id"), nullable=False, unique=True)
    entities: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    gaps: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    completeness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class FollowupQuestion(Base):
    """M7/M8: each generated follow-up question + the voice answer it maps to.

    Recording what was asked is what prevents repeats (M7 requirement); the answer
    IS an utterance (voice-only, ADR-0027) — never a free-text field.
    """

    __tablename__ = "followup_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    visit_id: Mapped[int] = mapped_column(ForeignKey("visits.id"), nullable=False, index=True)
    target_gap: Mapped[str | None] = mapped_column(String(255), nullable=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)  # shown AND spoken (TTS)
    priority: Mapped[int | None] = mapped_column(Integer, nullable=True)
    answer_utterance_id: Mapped[int | None] = mapped_column(
        ForeignKey("utterances.id"), nullable=True
    )
    asked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RiskAssessment(Base):
    """M10 — append-only: each assessment is a new row; the latest is current.

    Red flags are first-class (ADR-0024): ``red_flags`` lists the triggered
    life-threatening phrases and ``rule_overrode`` records that the RULE (not the
    model) forced the 'critical' tier — the safety story stays auditable.
    """

    __tablename__ = "risk_assessments"
    __table_args__ = (
        CheckConstraint(
            "tier IN ('low','medium','high','critical')", name="ck_risk_assessments_tier"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    visit_id: Mapped[int] = mapped_column(ForeignKey("visits.id"), nullable=False, index=True)
    tier: Mapped[str] = mapped_column(String(16), nullable=False)
    red_flags: Mapped[list | None] = mapped_column(JSON, nullable=True)  # [] if none
    rule_overrode: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    model_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class XaiExplanation(Base):
    """M11 — the plain-language reason for one specific risk assessment (1:1).
    Every risk output must have a stored reason (constitution); no disease names."""

    __tablename__ = "xai_explanations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    risk_assessment_id: Mapped[int] = mapped_column(
        ForeignKey("risk_assessments.id"), nullable=False, unique=True
    )
    reason_text: Mapped[str] = mapped_column(Text, nullable=False)
    drivers: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Report(Base):
    """M12 — the doctor-facing report. NO diagnosis (rule #2). Regenerable;
    ``sections`` is flexible JSON so the report can grow without migrations."""

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    visit_id: Mapped[int] = mapped_column(ForeignKey("visits.id"), nullable=False, index=True)
    risk_assessment_id: Mapped[int | None] = mapped_column(
        ForeignKey("risk_assessments.id"), nullable=True
    )
    sections: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class DoctorReview(Base):
    """M14 — doctor override + annotation. Append-only human-in-the-loop actions."""

    __tablename__ = "doctor_reviews"
    __table_args__ = (
        CheckConstraint(
            "override_tier IS NULL OR override_tier IN ('low','medium','high','critical')",
            name="ck_doctor_reviews_override_tier",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    visit_id: Mapped[int] = mapped_column(ForeignKey("visits.id"), nullable=False, index=True)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    override_tier: Mapped[str | None] = mapped_column(String(16), nullable=True)
    disposition: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Feedback(Base):
    """M15 — training signal for continuous learning; kept separate for later export."""

    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    visit_id: Mapped[int] = mapped_column(ForeignKey("visits.id"), nullable=False, index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1..5
    correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class AuditLog(Base):
    """Cross-cutting append-only audit trail (rule #4 + medical accountability).
    Deliberately LOOSE entity link (type + id strings) so any table is auditable
    without a hard FK per table."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    clinic_id: Mapped[int | None] = mapped_column(ForeignKey("clinics.id"), nullable=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ModuleEvent(Base):
    """Per-module execution log — THE extensibility keystone (principle 5) and the
    observability record for the free-tier strategy (provider, latency, fallback).
    Append-only; a future module is just a new module_code value.
    """

    __tablename__ = "module_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    visit_id: Mapped[int] = mapped_column(ForeignKey("visits.id"), nullable=False, index=True)
    module_code: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)  # ok | fallback | error
    provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Utterance(Base):
    __tablename__ = "utterances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Which visit this turn belongs to. Nullable: legacy rows were backfilled onto
    # synthetic visits in 0003, but pre-visit capture must still be able to store raw.
    visit_id: Mapped[int | None] = mapped_column(ForeignKey("visits.id"), nullable=True, index=True)

    # Speaker: 'patient' (spoken/typed input) or 'system' (a question spoken by TTS).
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="patient", server_default="patient")

    # Order of the turn within its visit. Nullable for legacy single-utterance sessions.
    seq: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # RAW — exactly what was recognized (mic) or typed (manual). Write-once, never edited.
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)

    # CORRECTED — a SEPARATE field, filled in later by the correction service. May be null.
    corrected_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Where the raw text came from: 'mic' or 'manual' (typed fallback).
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="mic")

    # Which STT engine produced the raw text (e.g. browser_webspeech, groq_whisper).
    stt_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Audit trail: which provider/model produced the correction.
    correction_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    correction_model: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    corrected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debug aid only
        return f"<Utterance id={self.id} source={self.source!r} corrected={self.corrected_text is not None}>"


class Document(Base):
    """A generated export artifact (.docx now, PDF later) for a completed session.

    The DB stays the source of truth (the Utterance holds the verbatim raw + the
    correction). A Document is a *derived* file, regenerable from the Utterance, so
    it never holds the canonical words — it just records what was exported and where.

    Two grains (rev 0010): legacy exports point at one ``utterance_id``; visit-grain
    exports (kind 'transcript' | 'summary_report' | 'prescription') point at
    ``visit_id`` only and leave ``utterance_id`` NULL.
    """

    __tablename__ = "documents"

    # Non-guessable string id (UUID). Doubles as the on-disk filename stem, so file
    # names leak nothing patient-identifying and are safe to expose in URLs.
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)

    # Which session (utterance) this document was generated from. NULL for
    # visit-grain exports, which have no single source utterance (rev 0010).
    utterance_id: Mapped[int | None] = mapped_column(
        ForeignKey("utterances.id"), nullable=True, index=True
    )

    # Which visit this export belongs to (aggregate root). Nullable: legacy exports
    # were backfilled from their utterance's synthetic visit in 0003.
    visit_id: Mapped[int | None] = mapped_column(ForeignKey("visits.id"), nullable=True, index=True)

    # Export format: "docx" today; "pdf" later — distinguishes multiple artifacts.
    format: Mapped[str] = mapped_column(String(8), nullable=False, default="docx")

    # Which transcript content this file holds: "raw" or "corrected" (raw and
    # corrected are exported as SEPARATE, independently downloadable files). Legacy
    # rows generated before this split are labelled "combined" via the server default.
    kind: Mapped[str] = mapped_column(String(16), nullable=False, server_default="combined")

    # Human-facing download name (e.g. "session-12-20260621.docx").
    filename: Mapped[str] = mapped_column(String(255), nullable=False)

    # Path RELATIVE to the configured documents_dir; resolved at read time so the
    # base directory can move (volume, object store) without rewriting rows.
    rel_path: Mapped[str] = mapped_column(String(512), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    def __repr__(self) -> str:  # pragma: no cover - debug aid only
        return f"<Document id={self.id!r} utterance_id={self.utterance_id} format={self.format!r}>"


class Prescription(Base):
    """DOCTOR-4/5/6 (rev 0010) — a doctor-authored prescription for one visit.

    ``payload`` is the whole form as JSON (patient info, symptoms, diagnosis,
    medicines[], advice, tests, follow-up date, language) so the shape can evolve
    without migrations (principle 3). The Diagnosis inside it is typed by the human
    doctor — NEVER AI-filled (rule #2, human decision C1). ``document_id`` links the
    exported .docx once generated; retrievable later by both doctor and patient.
    """

    __tablename__ = "prescriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    visit_id: Mapped[int] = mapped_column(ForeignKey("visits.id"), nullable=False, index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
