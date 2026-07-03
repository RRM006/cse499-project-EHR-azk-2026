"""doctor reviews + feedback (G5) — the human-in-the-loop tables (M14/M15).

Both append-only: overrides/annotations and the learning signal are history,
never overwritten.

Revision ID: 0008_doctor_reviews_feedback
Revises: 0007_reports
Create Date: 2026-07-03
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0008_doctor_reviews_feedback"
down_revision: Union[str, None] = "0007_reports"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "doctor_reviews",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("visit_id", sa.Integer(), nullable=False),
        sa.Column("reviewer_id", sa.Integer(), nullable=False),
        sa.Column("override_tier", sa.String(length=16), nullable=True),
        sa.Column("disposition", sa.String(length=64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["visit_id"], ["visits.id"]),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "override_tier IS NULL OR override_tier IN ('low','medium','high','critical')",
            name="ck_doctor_reviews_override_tier",
        ),
    )
    op.create_index("ix_doctor_reviews_visit_id", "doctor_reviews", ["visit_id"])
    op.create_table(
        "feedback",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("visit_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("correct", sa.Boolean(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["visit_id"], ["visits.id"]),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_feedback_visit_id", "feedback", ["visit_id"])


def downgrade() -> None:
    op.drop_index("ix_feedback_visit_id", table_name="feedback")
    op.drop_table("feedback")
    op.drop_index("ix_doctor_reviews_visit_id", table_name="doctor_reviews")
    op.drop_table("doctor_reviews")
