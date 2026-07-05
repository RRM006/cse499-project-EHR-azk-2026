"""STRUCT-1/STRUCT-2 — the legacy Phase-0 demo is isolated at /legacy/ and every
app entry point is reachable. The landing page at / links to all four portals so
nothing is orphaned by the move (context_fixed_problem.md §0.1).

Static mounts need no DB, so no fixture/lifespan here — plain TestClient.
"""

from fastapi.testclient import TestClient

from backend.app.main import ENTRY_POINTS, app

client = TestClient(app)


def test_all_entry_points_reachable():
    for name, path in ENTRY_POINTS:
        resp = client.get(path)
        assert resp.status_code == 200, f"{name} ({path}) returned {resp.status_code}"


def test_root_is_the_landing_page_linking_every_portal():
    html = client.get("/").text
    for target in ("/kiosk.html", "/medic/", "/doctor/", "/legacy/"):
        assert target in html, f"landing page must link to {target}"


def test_legacy_demo_is_served_at_legacy_not_root():
    legacy = client.get("/legacy/").text
    assert "Phase 0" in legacy  # the old demo's title/banner
    assert "Phase 0" not in client.get("/").text  # and it no longer owns the root


def test_legacy_assets_resolve_relative_to_legacy():
    # index.html now references styles.css/app.js relatively; both must resolve.
    assert client.get("/legacy/styles.css").status_code == 200
    assert client.get("/legacy/app.js").status_code == 200


def test_kiosk_and_its_script_still_served_from_root_mount():
    assert client.get("/kiosk.html").status_code == 200
    assert client.get("/kiosk.js").status_code == 200
