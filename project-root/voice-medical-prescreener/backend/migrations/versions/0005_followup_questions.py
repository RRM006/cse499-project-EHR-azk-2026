"""follow-up loop — followup_questions (G2)

Stage G2 of architecture.md's roadmap: each M7-generated question is recorded
(no repeats) and linked to the voice utterance that answers it (ADR-0027:
the answer IS an utterance, never a free-text field).

Revision ID: 0005_followup_questions
Revises: 0004_intake_profile
Create Date: 2026-07-03
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005_followup_questions"
down_revision: Union[str, None] = "0004_intake_profile"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "followup_questions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("visit_id", sa.Integer(), nullable=False),
        sa.Column("target_gap", sa.String(length=255), nullable=True),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=True),
        sa.Column("answer_utterance_id", sa.Integer(), nullable=True),
        sa.Column("asked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["visit_id"], ["visits.id"]),
        sa.ForeignKeyConstraint(["answer_utterance_id"], ["utterances.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_followup_questions_visit_id", "followup_questions", ["visit_id"])


def downgrade() -> None:
    op.drop_index("ix_followup_questions_visit_id", table_name="followup_questions")
    op.drop_table("followup_questions")
