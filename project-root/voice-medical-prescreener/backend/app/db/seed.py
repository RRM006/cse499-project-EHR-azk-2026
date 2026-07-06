"""Idempotent demo seeding for data that lives outside the migrations.

Currently: sample prescription letterhead (DOCTOR-4, rev 0010) for the demo clinic
and the seeded doctors. The letterhead columns are NULL after migration 0010; this
fills sensible sample values ONLY where a field is still NULL, so it never clobbers a
real edit and is safe to run on every startup.

Human decision (Session 13): letterhead is seeded + editable IN the prescription form;
those edits ride inside the prescription payload and are NOT written back here — so the
seeded profile values stay put and are reused as the prefill for every prescription.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.db.models import Clinic, User


def seed_demo_letterhead(db: Session) -> None:
    """Fill NULL letterhead fields on the demo clinic + doctors with sample values."""
    changed = False

    clinic = db.query(Clinic).order_by(Clinic.id).first()
    if clinic is not None and clinic.address is None:
        clinic.address = (
            "House 12, Road 5, Dhanmondi, Dhaka 1205, Bangladesh · Tel: +880 2-9XXXXXX"
        )
        changed = True
        # logo_path is left None on purpose: no image asset ships with the repo, so the
        # DOCTOR-6 .docx (step 19) falls back to the clinic name as a text letterhead.

    for doctor in db.query(User).filter(User.role == "doctor").order_by(User.id).all():
        if doctor.qualification is None:
            doctor.qualification = "MBBS, FCPS (Medicine)"
            changed = True
        if doctor.registration_no is None:
            doctor.registration_no = f"BMDC-A-{40000 + doctor.id}"
            changed = True
        if doctor.specialization is None:
            doctor.specialization = "Internal Medicine"
            changed = True
        # signature_path left None: the .docx renders a signature line instead of an image.

    if changed:
        db.commit()
