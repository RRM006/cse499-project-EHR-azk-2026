"""otp_codes — real OTP verification (P4-1, ADR-0045).

Replaces the ADR-0030 stub compare with DB-backed verification behind a
pluggable sender seam (dev log / TextBee SMS). Stores only a salted SHA-256
HASH of each code (never plaintext), with 5-minute expiry, per-code attempt
counting (lockout) and single-use consumption. Keyed by the normalized phone
("+8801...") because verification happens before a visit exists;
``patient_id`` is a nullable audit link.

Revision ID: 0012_otp_codes
Revises: 0011_visit_submitted_at
Create Date: 2026-07-11
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0012_otp_codes"
down_revision: Union[str, None] = "0011_visit_submitted_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "otp_codes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=True),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("salt", sa.String(length=32), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_otp_codes_phone", "otp_codes", ["phone"])


def downgrade() -> None:
    op.drop_index("ix_otp_codes_phone", table_name="otp_codes")
    op.drop_table("otp_codes")
