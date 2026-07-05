"""Bilingual summary values (step 5 of the Session-9 plan) — fully offline.

Proves the back-compat contract: pre-Session-9 rows (plain ``{value}``) still parse,
score, and render; the new {"en","bn"} model reply lands as value/value_en/value_bn;
a plain-string model reply (salvage) is treated as English; and a staff PATCH edit
writes the typed text into ALL language slots untranslated (authoritative, no quota).
"""

from backend.app.schemas.profile import SUMMARY_FIELD_KEYS, SummaryFields
from backend.app.services.completion import completeness_score, field_has_text
from backend.app.services.intake import _to_summary_fields


class _P:  # minimal CaseProfile stand-in for completeness_score
    def __init__(self, fields):
        self.entities = {"summary_fields": fields}


def test_bilingual_reply_fills_all_three_slots():
    fields = _to_summary_fields(
        {"main_problem": {"en": "Headache", "bn": "মাথা ব্যথা"}}
    ).model_dump(mode="json")
    f = fields["main_problem"]
    assert f["value"] == "Headache"        # mirrors value_en (back-compat)
    assert f["value_en"] == "Headache"
    assert f["value_bn"] == "মাথা ব্যথা"
    assert f["source"] == "ai"


def test_plain_string_reply_is_salvaged_as_english():
    fields = _to_summary_fields({"allergies": "No known allergies"}).model_dump(mode="json")
    f = fields["allergies"]
    assert f["value"] == f["value_en"] == "No known allergies"
    assert f["value_bn"] == ""


def test_legacy_value_only_rows_still_validate_and_score():
    # A stored pre-Session-9 profile: only {value, source} per field.
    legacy = {k: {"value": "something", "source": "ai"} for k in SUMMARY_FIELD_KEYS[:6]}
    # Pydantic shape still accepts it (new slots default to "").
    parsed = SummaryFields.model_validate(legacy).model_dump(mode="json")
    assert parsed["main_problem"]["value"] == "something"
    assert parsed["main_problem"]["value_bn"] == ""
    # M9 counts legacy fields as filled — 6 of 10.
    assert completeness_score(_P(legacy)) == 0.6


def test_field_has_text_checks_every_slot():
    assert field_has_text({"value": "x"})
    assert field_has_text({"value_en": "x"})
    assert field_has_text({"value_bn": "শুধু বাংলা"})  # Bangla-only still counts
    assert not field_has_text({"value": " ", "value_en": "", "value_bn": None})
    assert not field_has_text(None)


def test_bn_only_extraction_counts_as_filled():
    # If the model fills only bn for a field, the field is NOT considered missing.
    fields = _to_summary_fields(
        {"current_concern": {"en": "", "bn": "দ্রুত সুস্থ হতে চাই"}}
    ).model_dump(mode="json")
    assert completeness_score(_P({"current_concern": fields["current_concern"]})) == 0.1
