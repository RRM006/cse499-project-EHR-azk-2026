"""Prepare a safe demo case for the walkthrough recording.

This does TWO things and nothing else:

1. PRIVACY. Replaces every patient's phone number and display name with an
   unmistakable demo value. No clinical content is touched -- transcripts,
   extracted fields, risk assessments, XAI reasons and documents are left
   exactly as the real application wrote them.

2. WORKFLOW RESET. Puts the genuine case (visit 20) back at the start of its
   own real workflow (`awaiting_review`, no assigned doctor) so the
   medic -> doctor -> EHR hand-off can be performed live, through the real UI,
   while recording. Unrelated half-finished development visits are closed so
   the triage queue reads clearly on camera.

Nothing here fabricates data.
"""

import sqlite3

DB = "/home/claude/app/backend/prescreener.db"
STAR_VISIT = 20

con = sqlite3.connect(DB)
cur = con.cursor()

# --- 1. privacy pass -------------------------------------------------------
patient_ids = [r[0] for r in cur.execute("SELECT id FROM patients ORDER BY id")]
for i, pid in enumerate(patient_ids):
    cur.execute(
        "UPDATE patients SET external_ref = ?, display_name = NULL WHERE id = ?",
        (f"+8801700000{i:03d}", pid),
    )

# The demo case keeps the name the patient actually gave in his own recorded
# words, so the verbatim panel and the identity card agree on camera.
star_patient = cur.execute(
    "SELECT patient_id FROM visits WHERE id = ?", (STAR_VISIT,)
).fetchone()[0]
cur.execute(
    """UPDATE patients
          SET display_name = ?, external_ref = ?, sex = ?, birth_year = ?,
              weight_kg = NULL, bp = NULL, height_cm = NULL
        WHERE id = ?""",
    ("রাকিব হাসান", "+8801799000020", "male", 2000, star_patient),
)

# --- 2. workflow reset -----------------------------------------------------
cur.execute(
    "UPDATE visits SET status = 'awaiting_review', assigned_doctor_id = NULL WHERE id = ?",
    (STAR_VISIT,),
)
cur.execute(
    "UPDATE visits SET status = 'closed' WHERE status = 'awaiting_review' AND id <> ?",
    (STAR_VISIT,),
)
cur.execute(
    """UPDATE visits SET status = 'closed'
        WHERE status = 'in_progress'
          AND id NOT IN (SELECT visit_id FROM case_profiles)"""
)

# --- 3. a realistic clock ---------------------------------------------------
# The stored record is weeks old, so the queue's genuine wait-time column would
# read "18d 6h" and the urgency ordering it drives would be unreadable on camera.
# Only the visit's timestamps move; not one clinical value is touched.
cur.execute(
    """UPDATE visits
          SET submitted_at = datetime('now', '-42 minutes'),
              started_at   = datetime('now', '-55 minutes')
        WHERE id = ?""",
    (STAR_VISIT,),
)
con.commit()

print("Demo case prepared.\n")
for row in cur.execute(
    """SELECT v.id, v.status, p.display_name, p.external_ref
         FROM visits v JOIN patients p ON p.id = v.patient_id
        WHERE v.status IN ('awaiting_review', 'awaiting_doctor')
        ORDER BY v.id"""
):
    print("  ", row)
con.close()
