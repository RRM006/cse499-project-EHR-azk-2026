"""aggregate root — clinics, users, patients, visits (G0 + ADR-0030 deltas)

Stage G0 of architecture.md's roadmap, plus the three reconciliation deltas approved in
ADR-0030 / architecture.md §7:
  * users.role CHECK includes 'medic' (triage role from the mockup);
  * visits.status CHECK includes 'awaiting_doctor' (medic -> doctor hand-off);
  * visits.assigned_doctor_id (nullable FK) records the medic's doctor assignment.

Also adds visit_id/role/seq to utterances and visit_id to documents (batch mode — SQLite
table rebuild preserving every row), backfills each legacy utterance onto its own
synthetic CLOSED visit (the old session grain was one utterance = one session), and
seeds the demo staff: 1 clinic, 1 medic, 2 doctors, 1 admin.

RAW transcript columns are untouched (rule #1).

Revision ID: 0003_aggregate_root
Revises: 0002_add_stt_provider_and_doc_kind
Create Date: 2026-07-03
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_aggregate_root"
down_revision: Union[str, None] = "0002_add_stt_provider_and_doc_kind"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def upgrade() -> None:
    # --- New core tables (architecture.md §2, with ADR-0030 deltas) ---
    op.create_table(
        "clinics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("clinic_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.CheckConstraint("role IN ('doctor','medic','desk','admin')", name="ck_users_role"),
    )
    op.create_table(
        "patients",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("clinic_id", sa.Integer(), nullable=False),
        sa.Column("external_ref", sa.String(length=64), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("sex", sa.String(length=16), nullable=True),
        sa.Column("birth_year", sa.Integer(), nullable=True),
        sa.Column("consent", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("clinic_id", "external_ref", name="uq_patients_clinic_external_ref"),
    )
    op.create_table(
        "visits",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.String(length=36), nullable=False),
        sa.Column("clinic_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=True),
        sa.Column("assigned_doctor_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="in_progress"),
        sa.Column("language", sa.String(length=8), nullable=False, server_default="bn-BD"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["assigned_doctor_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
        sa.CheckConstraint(
            "status IN ('in_progress','awaiting_review','awaiting_doctor','reviewed','closed')",
            name="ck_visits_status",
        ),
    )

    # --- Attach existing tables to the aggregate root (batch = SQLite rebuild) ---
    with op.batch_alter_table("utterances") as batch:
        batch.add_column(
            sa.Column(
                "visit_id",
                sa.Integer(),
                sa.ForeignKey("visits.id", name="fk_utterances_visit_id"),
                nullable=True,
            )
        )
        batch.add_column(
            sa.Column("role", sa.String(length=16), nullable=False, server_default="patient")
        )
        batch.add_column(sa.Column("seq", sa.Integer(), nullable=True))
    op.create_index("ix_utterances_visit_id", "utterances", ["visit_id"])

    with op.batch_alter_table("documents") as batch:
        batch.add_column(
            sa.Column(
                "visit_id",
                sa.Integer(),
                sa.ForeignKey("visits.id", name="fk_documents_visit_id"),
                nullable=True,
            )
        )
    op.create_index("ix_documents_visit_id", "documents", ["visit_id"])

    # --- Seed: 1 clinic + demo staff (1 medic, 2 doctors, 1 admin) ---
    bind = op.get_bind()
    now = _now()
    bind.execute(
        sa.text("INSERT INTO clinics (id, name, created_at) VALUES (1, 'Demo Clinic', :now)"),
        {"now": now},
    )
    for name, role, email in [
        ("Medic Rahman", "medic", "medic.rahman@demo.clinic"),
        ("Dr. M. Rahman", "doctor", "dr.m_rahman@demo.clinic"),
        ("Dr. Yasmin Ara", "doctor", "dr.yasmin@demo.clinic"),
        ("Admin", "admin", "admin@demo.clinic"),
    ]:
        bind.execute(
            sa.text(
                "INSERT INTO users (clinic_id, name, role, email, created_at) "
                "VALUES (1, :name, :role, :email, :now)"
            ),
            {"name": name, "role": role, "email": email, "now": now},
        )

    # --- Backfill: each legacy utterance was its own session -> its own closed visit ---
    rows = bind.execute(sa.text("SELECT id, created_at FROM utterances WHERE visit_id IS NULL")).fetchall()
    for utt_id, created_at in rows:
        visit_uuid = str(uuid.uuid4())
        bind.execute(
            sa.text(
                "INSERT INTO visits (uuid, clinic_id, status, language, started_at, completed_at) "
                "VALUES (:u, 1, 'closed', 'bn-BD', :ts, :ts)"
            ),
            {"u": visit_uuid, "ts": created_at},
        )
        visit_id = bind.execute(
            sa.text("SELECT id FROM visits WHERE uuid = :u"), {"u": visit_uuid}
        ).scalar()
        bind.execute(
            sa.text("UPDATE utterances SET visit_id = :v, seq = 0 WHERE id = :i"),
            {"v": visit_id, "i": utt_id},
        )
    bind.execute(
        sa.text(
            "UPDATE documents SET visit_id = "
            "(SELECT visit_id FROM utterances WHERE utterances.id = documents.utterance_id) "
            "WHERE visit_id IS NULL"
        )
    )


def downgrade() -> None:
    op.drop_index("ix_documents_visit_id", table_name="documents")
    with op.batch_alter_table("documents") as batch:
        batch.drop_column("visit_id")
    op.drop_index("ix_utterances_visit_id", table_name="utterances")
    with op.batch_alter_table("utterances") as batch:
        batch.drop_column("seq")
        batch.drop_column("role")
        batch.drop_column("visit_id")
    op.drop_table("visits")
    op.drop_table("patients")
    op.drop_table("users")
    op.drop_table("clinics")
