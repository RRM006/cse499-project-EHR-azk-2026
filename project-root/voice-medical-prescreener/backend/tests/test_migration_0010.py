"""DB gates for rev 0010 (visit-grain documents + demographics + letterhead + prescriptions).

Same throwaway-SQLite-file approach as test_migration_0003. Proves:
  * a legacy DB with data upgrades in place — RAW text byte-identical (rule #1) and the
    existing document keeps its utterance_id even though the column is now nullable;
  * a fresh DB builds to head with the prescriptions table and every new column;
  * a visit-grain document row (utterance_id NULL, kind 'summary_report') inserts
    cleanly — the seam that steps 3/15/19 of the Session-9 plan build on;
  * a prescription row round-trips its JSON payload.
"""

import json

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from backend.app.db.database import _ALEMBIC_INI


def _cfg(url: str) -> Config:
    cfg = Config(str(_ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def _cols(engine, table):
    return {c["name"]: c for c in inspect(engine).get_columns(table)}


def _fresh_engine(tmp_path, name="fresh.db"):
    url = f"sqlite:///{(tmp_path / name).as_posix()}"
    command.upgrade(_cfg(url), "head")
    return create_engine(url, future=True)


def test_legacy_db_upgrades_keeping_raw_and_document_link(tmp_path):
    url = f"sqlite:///{(tmp_path / 'legacy.db').as_posix()}"
    engine = create_engine(url, future=True)
    command.upgrade(_cfg(url), "0002_add_stt_provider_and_doc_kind")
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO utterances (raw_text, source, created_at) "
                "VALUES ('পেট ব্যথা দুই দিন', 'mic', '2026-07-05 09:00:00')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO documents (id, utterance_id, format, kind, filename, rel_path, created_at) "
                "VALUES ('doc-1', 1, 'docx', 'raw', 'f.docx', 'f.docx', '2026-07-05 09:01:00')"
            )
        )

    command.upgrade(_cfg(url), "head")

    with engine.connect() as conn:
        assert conn.execute(text("SELECT raw_text FROM utterances")).scalar() == "পেট ব্যথা দুই দিন"
        # The pre-existing document keeps its utterance link across the rebuild.
        assert conn.execute(text("SELECT utterance_id FROM documents")).scalar() == 1


def test_fresh_db_has_prescriptions_table_and_new_columns(tmp_path):
    engine = _fresh_engine(tmp_path)
    assert "prescriptions" in inspect(engine).get_table_names()
    assert {"id", "visit_id", "doctor_id", "payload", "document_id",
            "created_at", "updated_at"} <= set(_cols(engine, "prescriptions"))
    assert {"weight_kg", "bp"} <= set(_cols(engine, "patients"))
    assert {"qualification", "registration_no", "specialization",
            "signature_path"} <= set(_cols(engine, "users"))
    assert {"address", "logo_path"} <= set(_cols(engine, "clinics"))
    # utterance_id is now optional (visit-grain documents).
    assert _cols(engine, "documents")["utterance_id"]["nullable"] is True


def test_visit_grain_document_inserts_without_utterance(tmp_path):
    engine = _fresh_engine(tmp_path, "visitgrain.db")
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO visits (uuid, clinic_id, status, language, started_at) "
                "VALUES ('v-1', 1, 'awaiting_review', 'bn-BD', '2026-07-05 09:00:00')"
            )
        )
        visit_id = conn.execute(text("SELECT id FROM visits WHERE uuid = 'v-1'")).scalar()
        conn.execute(
            text(
                "INSERT INTO documents (id, utterance_id, visit_id, format, kind, filename, rel_path, created_at) "
                "VALUES ('doc-v1', NULL, :v, 'docx', 'summary_report', 'r.docx', 'r.docx', '2026-07-05 09:02:00')"
            ),
            {"v": visit_id},
        )
    with engine.connect() as conn:
        kind, utt = conn.execute(
            text("SELECT kind, utterance_id FROM documents WHERE id = 'doc-v1'")
        ).one()
        assert kind == "summary_report" and utt is None


def test_prescription_payload_round_trips(tmp_path):
    engine = _fresh_engine(tmp_path, "rx.db")
    payload = {
        "language": "bn",
        "diagnosis": "",  # authored by the human doctor only (rule #2 / decision C1)
        "medicines": [{"name": "Napa", "strength": "500mg", "dosage": "1+1+1",
                       "timing": "after meals", "duration": "3 days"}],
    }
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO visits (uuid, clinic_id, status, language, started_at) "
                "VALUES ('v-rx', 1, 'awaiting_doctor', 'bn-BD', '2026-07-05 09:00:00')"
            )
        )
        visit_id = conn.execute(text("SELECT id FROM visits WHERE uuid = 'v-rx'")).scalar()
        doctor_id = conn.execute(
            text("SELECT id FROM users WHERE role = 'doctor' LIMIT 1")
        ).scalar()
        conn.execute(
            text(
                "INSERT INTO prescriptions (visit_id, doctor_id, payload, created_at, updated_at) "
                "VALUES (:v, :d, :p, '2026-07-05 09:03:00', '2026-07-05 09:03:00')"
            ),
            {"v": visit_id, "d": doctor_id, "p": json.dumps(payload, ensure_ascii=False)},
        )
    with engine.connect() as conn:
        stored = json.loads(
            conn.execute(text("SELECT payload FROM prescriptions")).scalar()
        )
        assert stored == payload
