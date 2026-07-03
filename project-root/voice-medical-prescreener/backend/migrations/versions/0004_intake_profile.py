"""intake profile — case_profiles + module_events (G1)

Stage G1 of architecture.md's roadmap: the evolving per-visit structured profile
(M3 entities incl. the ADR-0030 summary_fields JSON shape, M4 summary, M6 gaps,
M9 completeness) and the append-only per-module execution log (provider / latency /
fallback — the extensibility keystone, principles 5 & 8).

Revision ID: 0004_intake_profile
Revises: 0003_aggregate_root
Create Date: 2026-07-03
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_intake_profile"
down_revision: Union[str, None] = "0003_aggregate_root"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "case_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("visit_id", sa.Integer(), nullable=False),
        sa.Column("entities", sa.JSON(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("gaps", sa.JSON(), nullable=True),
        sa.Column("completeness_score", sa.Float(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["visit_id"], ["visits.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("visit_id"),
    )
    op.create_table(
        "module_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("visit_id", sa.Integer(), nullable=False),
        sa.Column("module_code", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["visit_id"], ["visits.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_module_events_visit_id", "module_events", ["visit_id"])


def downgrade() -> None:
    op.drop_index("ix_module_events_visit_id", table_name="module_events")
    op.drop_table("module_events")
    op.drop_table("case_profiles")
