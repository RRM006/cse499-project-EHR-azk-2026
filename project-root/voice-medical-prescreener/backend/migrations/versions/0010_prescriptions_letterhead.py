"""visit-grain documents + demographics + letterhead + prescriptions table.

Spec: context_fixed_problem.md (KIOSK-4, MEDIC-6/7, DOCTOR-3/4/5/6), decisions locked
by the human in Session 9 (DB-backed prescriptions/reports; letterhead in DB).

- ``documents.utterance_id`` becomes NULLABLE: visit-grain exports (full-visit raw
  transcript, staff summary report, prescription) have no single source utterance.
  Existing rows keep their value. The new ``documents.kind`` values ('transcript',
  'summary_report', 'prescription') are data-level — ``kind`` has no CHECK
  constraint, so they need no DDL.
- ``patients`` gains weight_kg + bp (age/gender already exist as birth_year/sex).
- ``users`` gains the doctor letterhead fields, ``clinics`` gains address/logo_path.
- New ``prescriptions`` table: the form content lives in a ``payload`` JSON column so
  the prescription shape can evolve without migrations (architecture principle 3);
  ``document_id`` links the exported .docx once generated.

Revision ID: 0010_prescriptions_letterhead
Revises: 0009_audit_log
Create Date: 2026-07-05
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0010_prescriptions_letterhead"
down_revision: Union[str, None] = "0009_audit_log"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Visit-grain documents: a full-visit export has no single utterance.
    with op.batch_alter_table("documents") as batch:
        batch.alter_column("utterance_id", existing_type=sa.Integer(), nullable=True)

    with op.batch_alter_table("patients") as batch:
        batch.add_column(sa.Column("weight_kg", sa.Float(), nullable=True))
        batch.add_column(sa.Column("bp", sa.String(length=32), nullable=True))

    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("qualification", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("registration_no", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("specialization", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("signature_path", sa.String(length=512), nullable=True))

    with op.batch_alter_table("clinics") as batch:
        batch.add_column(sa.Column("address", sa.Text(), nullable=True))
        batch.add_column(sa.Column("logo_path", sa.String(length=512), nullable=True))

    op.create_table(
        "prescriptions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("visit_id", sa.Integer(), nullable=False),
        sa.Column("doctor_id", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["visit_id"], ["visits.id"], name="fk_prescriptions_visit_id"),
        sa.ForeignKeyConstraint(["doctor_id"], ["users.id"], name="fk_prescriptions_doctor_id"),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"], name="fk_prescriptions_document_id"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prescriptions_visit_id", "prescriptions", ["visit_id"])


def downgrade() -> None:
    op.drop_index("ix_prescriptions_visit_id", table_name="prescriptions")
    op.drop_table("prescriptions")
    with op.batch_alter_table("clinics") as batch:
        batch.drop_column("logo_path")
        batch.drop_column("address")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("signature_path")
        batch.drop_column("specialization")
        batch.drop_column("registration_no")
        batch.drop_column("qualification")
    with op.batch_alter_table("patients") as batch:
        batch.drop_column("bp")
        batch.drop_column("weight_kg")
    with op.batch_alter_table("documents") as batch:
        batch.alter_column("utterance_id", existing_type=sa.Integer(), nullable=False)
