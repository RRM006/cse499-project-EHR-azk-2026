"""visits.submitted_at — when the patient hit "Confirm & Submit".

Spec: context fixed problem 2.0.md P3-1 ("Patient Time"): the doctor portal must
show the patient's SUBMISSION date/time (Dhaka-rendered in the browser), which is
distinct from ``started_at`` (kiosk session start). Stamped by
``set_visit_status`` on the in_progress -> awaiting_review transition; nullable so
pre-existing visits (and unsubmitted ones) simply have none — the frontend falls
back to ``started_at`` for those.

Revision ID: 0011_visit_submitted_at
Revises: 0010_prescriptions_letterhead
Create Date: 2026-07-10
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0011_visit_submitted_at"
down_revision: Union[str, None] = "0010_prescriptions_letterhead"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("visits") as batch:
        batch.add_column(sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("visits") as batch:
        batch.drop_column("submitted_at")
