"""risk + XAI — risk_assessments + xai_explanations (G3)

Stage G3 of architecture.md's roadmap. risk_assessments is APPEND-ONLY (each
re-assessment is a new row) with first-class red flags and the rule_overrode
audit bit (ADR-0024: the rule-based red-flag check forces 'critical').
Every assessment gets a 1:1 xai_explanations reason (constitution / M11).

Revision ID: 0006_risk_xai
Revises: 0005_followup_questions
Create Date: 2026-07-03
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006_risk_xai"
down_revision: Union[str, None] = "0005_followup_questions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "risk_assessments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("visit_id", sa.Integer(), nullable=False),
        sa.Column("tier", sa.String(length=16), nullable=False),
        sa.Column("red_flags", sa.JSON(), nullable=True),
        sa.Column("rule_overrode", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("model_provider", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["visit_id"], ["visits.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "tier IN ('low','medium','high','critical')", name="ck_risk_assessments_tier"
        ),
    )
    op.create_index("ix_risk_assessments_visit_id", "risk_assessments", ["visit_id"])
    op.create_table(
        "xai_explanations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("risk_assessment_id", sa.Integer(), nullable=False),
        sa.Column("reason_text", sa.Text(), nullable=False),
        sa.Column("drivers", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["risk_assessment_id"], ["risk_assessments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("risk_assessment_id"),
    )


def downgrade() -> None:
    op.drop_table("xai_explanations")
    op.drop_index("ix_risk_assessments_visit_id", table_name="risk_assessments")
    op.drop_table("risk_assessments")
