"""patients.blood_glucose_mmol_l + blood_glucose_context (S39, ADR-0064).

S38 shipped the glucose REFERENCE chart (A6) but no place to record a patient's
actual reading — so a medic could read the published thresholds and had nowhere to
write the number they had just measured. This adds that place, and only that.

**Why two columns and not one.** S38's own finding was that there is no single
"diabetic limit": a glucose value means different things fasting, two hours into an
OGTT, and taken at random, and the reference chart is organised by exactly that
context. A bare number in a medical record is therefore not merely less useful, it is
unsafe — a fasting 6.5 and a random 6.5 are different facts. The context travels with
the value or neither is stored.

**Why it lives on ``patients``.** It is a staff-recorded vital, exactly like
``weight_kg`` (rev 0010) and ``height_cm`` (rev 0013): same row, same
``PATCH /api/patients/{id}/vitals`` endpoint, same audit action. No new table, no new
endpoint, no new permission.

**What is deliberately NOT added.**

* *No band, class or interpretation column.* The value is stored; whether it means
  anything is the clinician's judgement beside the published chart (rule #2, and the
  ADR-0060 rule that ``glucose_reference()`` takes no patient value).
* *No measured_at column.* ``audit_log`` already records when the value was written
  and by whom — the same derivation ADR-0060 used for the referral history — and
  weight and BP set the precedent of carrying no timestamp of their own.
* *No HbA1c.* It is a percentage, not mmol/L, and it is a laboratory result rather
  than the bedside reading a medic takes at intake. Storing it in a mmol/L column
  would put two different quantities in one place, which is the exact defect the
  context column exists to prevent. It stays on the reference chart only.

Revision ID: 0014_blood_glucose
Revises: 0013_height_and_clinical_notes
Create Date: 2026-08-14
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0014_blood_glucose"
down_revision: Union[str, None] = "0013_height_and_clinical_notes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("patients") as batch:
        batch.add_column(sa.Column("blood_glucose_mmol_l", sa.Float(), nullable=True))
        batch.add_column(sa.Column("blood_glucose_context", sa.String(length=16), nullable=True))
        # The context keys are the reference chart's own (services/clinical_reference).
        # Constrained in the database so a value can never arrive without a meaning
        # through some future caller that forgets to validate.
        batch.create_check_constraint(
            "ck_patients_glucose_context",
            "blood_glucose_context IS NULL OR "
            "blood_glucose_context IN ('fasting','ogtt_2h','random')",
        )


def downgrade() -> None:
    with op.batch_alter_table("patients") as batch:
        batch.drop_constraint("ck_patients_glucose_context", type_="check")
        batch.drop_column("blood_glucose_context")
        batch.drop_column("blood_glucose_mmol_l")
