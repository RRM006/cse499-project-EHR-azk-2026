"""baseline — schema as it existed before Alembic was adopted

This recreates the ORIGINAL tables (``utterances`` WITHOUT ``stt_provider`` and
``documents`` WITHOUT ``kind``) — exactly what ``Base.metadata.create_all`` produced
in Sessions 1–5. An existing database is *stamped* at this revision (no DDL runs),
so the real change lives in 0002. A fresh database runs this first, then 0002.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-06-21
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "utterances",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("corrected_text", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("correction_provider", sa.String(length=32), nullable=True),
        sa.Column("correction_model", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("corrected_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("utterance_id", sa.Integer(), nullable=False),
        sa.Column("format", sa.String(length=8), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("rel_path", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["utterance_id"], ["utterances.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_documents_utterance_id", "documents", ["utterance_id"])


def downgrade() -> None:
    op.drop_index("ix_documents_utterance_id", table_name="documents")
    op.drop_table("documents")
    op.drop_table("utterances")
