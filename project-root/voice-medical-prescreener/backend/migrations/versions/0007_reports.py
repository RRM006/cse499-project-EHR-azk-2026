"""reports (G4) — the M12 doctor-facing report table.

Sections are flexible JSON (grow without migrations); a report cites the exact
risk assessment it was built from (auditability). NO diagnosis (rule #2).

Revision ID: 0007_reports
Revises: 0006_risk_xai
Create Date: 2026-07-03
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007_reports"
down_revision: Union[str, None] = "0006_risk_xai"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("visit_id", sa.Integer(), nullable=False),
        sa.Column("risk_assessment_id", sa.Integer(), nullable=True),
        sa.Column("sections", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["visit_id"], ["visits.id"]),
        sa.ForeignKeyConstraint(["risk_assessment_id"], ["risk_assessments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reports_visit_id", "reports", ["visit_id"])


def downgrade() -> None:
    op.drop_index("ix_reports_visit_id", table_name="reports")
    op.drop_table("reports")
