"""patients.height_cm + the clinical_notes table (S38, ADR-0060).

The first migration since 0012, and it is deliberately small. S38's brief forbids
database redundancy and demands that a change be justified before it is made, so the
majority of the session's features shipped with NO schema change at all — the medic's
completed-referral list is derived from ``audit_log.actor_id``, per-field verification
rides inside the existing ``case_profiles.entities`` JSON, and the FHIR export is
assembled per request from rows that already exist. Two things could not be:

**1. ``patients.height_cm``.** BMI needs a height and the schema had nowhere to put one.
``patients`` already owns the staff-recorded vitals (``weight_kg``, ``bp``) from rev
0010, so height belongs in exactly that row and is edited through exactly that endpoint.
⚠ BMI itself is NOT stored, here or anywhere: it is a pure function of two columns that
are already present, and persisting it would create precisely the duplicate
representation the brief forbids — one that silently goes stale the moment a weight is
corrected.

**2. ``clinical_notes``.** Two requested features — the doctor's recall/follow-up
scheduling and the doctor→medic back-channel — are the same shape: an attributable,
visit-linked, typed note carrying free text, an optional due date and an open/closed
lifecycle. Neither fits an existing table. ``audit_log`` is append-only and means "what
happened", so hosting mutable workflow state in it would corrupt the audit trail's
meaning; ``doctor_reviews`` has no date and no lifecycle; the prescription's
``followup_date`` is a line on a document, not a queue anyone can work. Rather than two
near-identical tables, ONE table carries both kinds — the difference is a ``kind`` value,
not a schema.

Revision ID: 0013_height_and_clinical_notes
Revises: 0012_otp_codes
Create Date: 2026-08-14
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0013_height_and_clinical_notes"
down_revision: Union[str, None] = "0012_otp_codes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("patients") as batch:
        batch.add_column(sa.Column("height_cm", sa.Float(), nullable=True))

    op.create_table(
        "clinical_notes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("clinic_id", sa.Integer(), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("visit_id", sa.Integer(), sa.ForeignKey("visits.id"), nullable=False),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=True),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("recipient_role", sa.String(length=16), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.CheckConstraint("kind IN ('recall','handover_note')", name="ck_clinical_notes_kind"),
        sa.CheckConstraint(
            "status IN ('open','done','cancelled')", name="ck_clinical_notes_status"
        ),
        sa.CheckConstraint(
            "recipient_role IS NULL OR recipient_role IN ('doctor','medic','desk','admin')",
            name="ck_clinical_notes_recipient_role",
        ),
    )
    # The two queries this table actually serves: "the medic's inbox" (by role+status)
    # and "everything attached to this case" (by visit).
    op.create_index("ix_clinical_notes_visit_id", "clinical_notes", ["visit_id"])
    op.create_index("ix_clinical_notes_patient_id", "clinical_notes", ["patient_id"])
    op.create_index(
        "ix_clinical_notes_inbox", "clinical_notes", ["recipient_role", "status", "kind"]
    )


def downgrade() -> None:
    op.drop_index("ix_clinical_notes_inbox", table_name="clinical_notes")
    op.drop_index("ix_clinical_notes_patient_id", table_name="clinical_notes")
    op.drop_index("ix_clinical_notes_visit_id", table_name="clinical_notes")
    op.drop_table("clinical_notes")
    with op.batch_alter_table("patients") as batch:
        batch.drop_column("height_cm")
