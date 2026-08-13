"""S36 / Finding 6 (ADR-0057) — the patient leaves with their own raw transcript.

When a screening is submitted, the RAW conversation now downloads by itself. It is the
same export KIOSK-4 already built and the same endpoint the button already used — what
changed is that nobody has to find the button, which on a kiosk aimed at elderly and
non-technical patients is the difference between a record they have and one they do not.

Two rules shape it, and both are rule #1 rules:

  * **RAW, never corrected.** `render_visit_transcript()` writes `u.raw_text` and the
    document says so on its first line. There is no path from the auto-download to the
    summary report, which is the artifact that DOES contain derived text.
  * **Exactly once, and never the wrong patient's.** The download is fired from the one
    guarded submit, carries its own guard on top, and — because it is an async render —
    is dropped entirely if the kiosk has been handed to the next patient before the file
    comes back. A missed download is the cheaper failure: the button and both staff
    portals can still produce it, whereas saving one patient's transcript into the next
    patient's browser is the exact leak Finding 2 exists to prevent.

The download NAME changed too. "transcript" is ambiguous once a corrected text exists in
the same system, so the human-facing filename is now `raw-transcript-visit-<8 chars of
visit uuid>-<date>.docx` — it says which of the two a doctor is holding without opening
it. The stored `kind` is unchanged, so the API contract and VISIT_DOCUMENT_KINDS are
untouched. It deliberately carries NO name and NO phone number: a filename ends up in a
downloads folder, an email subject and a shared file listing (rule #4).

⚠ Scope: real backend renders here, plus the shipped kiosk driven in a browser engine
with the anchor click intercepted and counted:

    finish a screening          1 download, 1 POST, name raw-transcript-visit-…docx
    three finish events         0 further downloads, 0 further POSTs
    endpoint used               /documents/transcript only — summary_report never hit
    reset mid-render            0 downloads (the stale file is dropped)
    manual button afterwards    1 download, still works
"""

from io import BytesIO

import pytest
from docx import Document as DocxDocument
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.database import Base, get_db
from backend.app.db.models import Clinic, Patient, Utterance, Visit
from backend.app.main import app
from backend.app.services.documents.storage import FilesystemStorage

client = TestClient(app)


def kiosk_js() -> str:
    resp = client.get("/kiosk.js")
    assert resp.status_code == 200
    return resp.text


def fn_body(name: str) -> str:
    js = kiosk_js()
    marker = f"function {name}("
    assert marker in js, f"{name}() is gone from the shipped kiosk"
    return js.split(marker)[1].split("\n}")[0]


@pytest.fixture()
def env(tmp_path, monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool, future=True)
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, future=True)

    db = TestSession()
    clinic = Clinic(name="Demo Clinic")
    db.add(clinic)
    db.flush()
    patient = Patient(clinic_id=clinic.id, external_ref="+8801712345678",
                      display_name="Kamal Hossain")
    db.add(patient)
    db.flush()
    spoken = Visit(clinic_id=clinic.id, patient_id=patient.id, status="awaiting_review")
    silent = Visit(clinic_id=clinic.id, patient_id=patient.id, status="awaiting_review")
    db.add_all([spoken, silent])
    db.flush()
    db.add(Utterance(visit_id=spoken.id, role="patient", seq=0,
                     raw_text="আমার তিন দিন ধরে মাথা ব্যথা", source="mic"))
    db.commit()
    uuids = (spoken.uuid, silent.uuid)
    db.close()

    def override_get_db():
        s = TestSession()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db
    storage = FilesystemStorage(tmp_path)
    monkeypatch.setattr("backend.app.services.documents.build_storage",
                        lambda *a, **k: storage)
    monkeypatch.setattr("backend.app.api.routes_documents.build_storage",
                        lambda *a, **k: storage)
    yield TestClient(app), uuids
    app.dependency_overrides.clear()


def _docx_text(content: bytes) -> str:
    doc = DocxDocument(BytesIO(content))
    return "\n".join(p.text for p in doc.paragraphs)


# --- the artifact itself ---


def test_the_download_name_says_which_transcript_this_is(env):
    """"transcript" is ambiguous once a corrected text exists in the same system."""
    c, (visit_uuid, _) = env
    body = c.post(f"/api/visits/{visit_uuid}/documents/transcript").json()
    assert body["filename"].startswith("raw-transcript-visit-")
    assert body["filename"].endswith(".docx")
    assert visit_uuid[:8] in body["filename"]
    assert body["kind"] == "transcript", "the stored kind is the API contract — unchanged"


def test_the_name_carries_no_patient_identity(env):
    """A filename ends up in a downloads folder, an email subject and a file listing."""
    c, (visit_uuid, _) = env
    filename = c.post(f"/api/visits/{visit_uuid}/documents/transcript").json()["filename"]
    for secret in ("Kamal", "Hossain", "8801712345678", "1712345678"):
        assert secret not in filename
    assert visit_uuid not in filename, "only the 8-char prefix, not the whole visit uuid"


def test_the_summary_report_keeps_its_own_name(env):
    """Only the transcript kind is relabelled — the other export is not a raw anything."""
    c, (visit_uuid, _) = env
    body = c.post(f"/api/visits/{visit_uuid}/documents/summary_report").json()
    assert body["filename"].startswith("summary_report-visit-")


def test_the_downloaded_bytes_are_the_raw_words(env):
    c, (visit_uuid, _) = env
    body = c.post(f"/api/visits/{visit_uuid}/documents/transcript").json()
    text = _docx_text(c.get(body["download_url"]).content)
    assert "আমার তিন দিন ধরে মাথা ব্যথা" in text
    assert "Raw (Verbatim)" in text
    assert "Nothing has been edited, corrected, or summarized." in text


def test_a_visit_with_no_speech_still_produces_a_valid_file(env):
    """Empty-transcript behaviour. A screening cannot normally be submitted empty, but
    the auto-download must not be the thing that throws if one ever is — it fires on a
    visit that has ALREADY been accepted by the server."""
    c, (_, silent_uuid) = env
    r = c.post(f"/api/visits/{silent_uuid}/documents/transcript")
    assert r.status_code == 200, r.text
    d = c.get(r.json()["download_url"])
    assert d.status_code == 200
    assert "Raw (Verbatim)" in _docx_text(d.content)   # a header-only document, not an error


# --- the kiosk wiring ---


def test_the_download_fires_from_the_one_guarded_submit():
    """Repeated finish events cannot create multiple downloads, because they cannot
    create multiple submits — the S34 `submitting` guard is never released on success."""
    submit = kiosk_js().split("async function confirmSubmit() {")[1].split("\n}\n")[0]
    assert "downloadRawTranscript({ auto: true });" in submit
    after_success = submit.split("setAvatarOverride('done');")[1]
    assert "downloadRawTranscript({ auto: true });" in after_success, \
        "the download must be on the SUCCESS path only — a refused submit has nothing to export"


def test_the_download_carries_its_own_once_guard():
    js = kiosk_js()
    assert "let autoTranscriptDownloaded = false;" in js
    body = fn_body("downloadRawTranscript")
    assert "if (auto && autoTranscriptDownloaded) return;" in body
    assert "if (auto) autoTranscriptDownloaded = true;" in body


def test_the_guard_is_cleared_for_the_next_patient():
    assert "autoTranscriptDownloaded = false;" in fn_body("endSession")


def test_the_finish_screen_never_waits_on_the_render():
    """Not awaited: the "all done" screen and its 5-second countdown must not sit behind
    a .docx render, and a failed download must not hold up an accepted visit."""
    submit = kiosk_js().split("async function confirmSubmit() {")[1].split("\n}\n")[0]
    assert "await downloadRawTranscript" not in submit


def test_a_stale_render_is_dropped_rather_than_handed_to_the_next_patient():
    body = fn_body("downloadRawTranscript")
    assert "const mine = sessionToken();" in body
    assert "if (!mine()) return;" in body
    assert body.index("if (!mine()) return;") < body.index("a.click();")


def test_the_automatic_download_fails_silently_but_the_button_does_not():
    """An error banner over the "all done" screen tells the patient about something they
    cannot act on, for a visit that was submitted successfully anyway. A patient who
    PRESSED the button is owed the opposite."""
    body = fn_body("downloadRawTranscript")
    assert "if (!auto && mine()) showError(e.message);" in body


def test_it_exports_the_raw_kind_and_nothing_derived():
    body = fn_body("downloadRawTranscript")
    assert "/documents/transcript`" in body
    assert "summary_report" not in body
