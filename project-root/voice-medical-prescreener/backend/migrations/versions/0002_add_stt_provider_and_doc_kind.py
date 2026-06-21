"""add utterances.stt_provider and documents.kind

Fixes the live bug ``table utterances has no column named stt_provider`` (the model
gained the column in Session 3 but the on-disk table never did, because create_all
never alters existing tables). Also adds ``documents.kind`` so raw and corrected
transcripts are exported as separate, independently downloadable files.

batch_alter_table is used because SQLite cannot ADD COLUMN with a server default in
place — Alembic rebuilds the table, preserving every existing row.

Revision ID: 0002_add_stt_provider_and_doc_kind
Revises: 0001_baseline
Create Date: 2026-06-21
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_add_stt_provider_and_doc_kind"
down_revision: Union[str, None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The bug fix: bring the table up to the model (nullable — pre-existing rows
    # simply have no provider recorded).
    with op.batch_alter_table("utterances") as batch:
        batch.add_column(sa.Column("stt_provider", sa.String(length=32), nullable=True))

    # Existing exports (none today) are labelled "combined" via the server default;
    # new code writes "raw" / "corrected".
    with op.batch_alter_table("documents") as batch:
        batch.add_column(
            sa.Column(
                "kind",
                sa.String(length=16),
                nullable=False,
                server_default="combined",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("documents") as batch:
        batch.drop_column("kind")
    with op.batch_alter_table("utterances") as batch:
        batch.drop_column("stt_provider")
