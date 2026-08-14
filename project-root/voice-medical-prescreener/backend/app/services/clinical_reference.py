"""S38 — STATIC clinical reference data: BMI bands, glucose reference ranges, and the
diagnostic-test vocabulary the doctor's "Required Tests" field suggests from.

⚠ WHAT THIS MODULE IS NOT. It is not a diagnosis engine, a rules engine, or a decision
support system, and nothing here may grow into one (rule #2, and the human's explicit
instruction on A6: *"Do not turn the UI into a diagnosis engine"*). Every function is a
pure lookup or a pure arithmetic conversion over values a HUMAN typed. Nothing reads a
patient row, nothing calls an LLM, nothing writes anything, and no function returns a
conclusion about a person — :func:`bmi_band` returns the band a number falls in, exactly
as a printed chart on a clinic wall does, and :func:`glucose_reference` returns the
chart itself with no patient value involved at all.

WHY THERE IS NO TABLE FOR ANY OF THIS. These are constants, not clinic data: they are
identical for every clinic, they change when a standards body publishes (not when a user
acts), and nothing ever queries or joins them. A table would add a migration, a seed, a
drift risk between deployments, and an admin surface — to store three lists that belong
in version control where a reviewer can see them change. The human's brief says the same
thing about the test list: *"Do NOT create a database table just for a static test
suggestion list unless there is a real persistence requirement."* There is none.

--------------------------------------------------------------------------------
ON THE GLUCOSE NUMBERS (A6 — the "diabetic limit" request)
--------------------------------------------------------------------------------

The human asked for "a diabetic limit". There is no such single number, and shipping one
would be the most dangerous thing in this file. What exists is a set of thresholds that
are only meaningful ALONGSIDE the measurement context, and which two major bodies define
differently at the lower bound. So this module ships the whole table — every context,
both unit systems, and the WHO/ADA disagreement stated out loud — rather than a number.

Values below are the published diagnostic thresholds of:
  * WHO/IDF (2006), *Definition and diagnosis of diabetes mellitus and intermediate
    hyperglycaemia* — the reference Bangladesh's national guidance follows;
  * WHO (2011) on HbA1c;
  * the American Diabetes Association's Standards of Care, which uses a LOWER fasting
    cut-off for the impaired-fasting-glucose band (5.6 vs 6.1 mmol/L). That difference
    is surfaced, not silently resolved, because a value of 5.8 mmol/L is "normal" under
    one standard and "impaired" under the other — which is precisely why a number on its
    own cannot be read as a finding.

Every payload carries ``requires_context`` and a disclaimer: a single reading never
establishes diabetes. WHO requires confirmation on a separate day unless there is
unequivocal hyperglycaemia with symptoms, and the diagnosis is the doctor's (rule #2).

--------------------------------------------------------------------------------
ON THE BMI BANDS (A5)
--------------------------------------------------------------------------------

Two ladders are returned, and both matter here. The WHO INTERNATIONAL bands are what
"BMI 26 = overweight" means worldwide. The WHO ASIAN bands (WHO Expert Consultation,
*Lancet* 2004) exist because cardiometabolic risk rises at a lower BMI in South Asian
populations — for a clinic in Bangladesh, reporting only the international ladder would
under-state risk for the actual patients. The band is reported under both, labelled, and
never converted into advice.
"""

from __future__ import annotations

#: Reference sources, quoted back with every payload so a reader can check them.
SOURCE_WHO_DIABETES = "WHO/IDF (2006) — Definition and diagnosis of diabetes mellitus and intermediate hyperglycaemia"
SOURCE_WHO_HBA1C = "WHO (2011) — Use of glycated haemoglobin (HbA1c) in the diagnosis of diabetes mellitus"
SOURCE_ADA = "American Diabetes Association — Standards of Care (classification and diagnosis)"
SOURCE_WHO_BMI = "WHO (1995/2000) BMI classification"
SOURCE_WHO_BMI_ASIA = "WHO Expert Consultation (2004), Lancet 363:157-163 — Asian BMI action points"

#: Attached to every reference payload. Rule #2 in one sentence, in both languages.
#: Deliberately generic: it rides on a BMI band and on the glucose chart alike, so it
#: says what is true of BOTH — a measurement is not a finding. The glucose-specific
#: point ("a single reading proves nothing without its context") lives in that chart's
#: own per-context text, where it is actually about something.
REFERENCE_DISCLAIMER = (
    "Reference values only — NOT a diagnosis. A measurement means nothing without the "
    "patient's clinical context; the interpretation and the decision are the doctor's."
)
REFERENCE_DISCLAIMER_BN = (
    "শুধুমাত্র রেফারেন্স মান — রোগনির্ণয় নয়। রোগীর সার্বিক অবস্থা ছাড়া কোনো পরিমাপ দিয়ে "
    "সিদ্ধান্ত নেওয়া যায় না; ব্যাখ্যা ও সিদ্ধান্ত ডাক্তারের।"
)

# ---------------------------------------------------------------------------
# BMI
# ---------------------------------------------------------------------------

#: Plausible human bounds. Outside these a BMI is not "unusual", it is a typo — a
#: 1.7 kg patient or a 17 cm one — and the human's brief is explicit: *"Do not allow
#: nonsensical values to produce misleading BMI."* Refusing to compute is the correct
#: answer; a number the staff would have to know to distrust is the wrong one.
MIN_WEIGHT_KG = 1.0
MAX_WEIGHT_KG = 500.0
MIN_HEIGHT_CM = 30.0
MAX_HEIGHT_CM = 260.0

#: (upper_exclusive_bound, code). The last band is open-ended (None).
_BMI_WHO: tuple[tuple[float | None, str], ...] = (
    (18.5, "underweight"),
    (25.0, "normal"),
    (30.0, "overweight"),
    (None, "obese"),
)

#: WHO Asian action points — deliberately different, and labelled as risk, not weight.
_BMI_ASIA: tuple[tuple[float | None, str], ...] = (
    (18.5, "underweight"),
    (23.0, "normal"),
    (27.5, "increased_risk"),
    (None, "high_risk"),
)

#: Codes on the wire; the two portals hold the bilingual labels (ADR-0030 f).
BMI_BAND_CODES = ("underweight", "normal", "overweight", "obese", "increased_risk", "high_risk")


def bmi(weight_kg: float | None, height_cm: float | None) -> float | None:
    """kg / m², rounded to one decimal — or None when the inputs cannot support one.

    None is returned for a missing value AND for an out-of-range one, so a caller can
    never accidentally render a BMI derived from a typo. The unit assumption is in the
    signature and is echoed to the user in the UI: **kilograms and centimetres**.
    """
    if weight_kg is None or height_cm is None:
        return None
    try:
        w = float(weight_kg)
        h = float(height_cm)
    except (TypeError, ValueError):
        return None
    if not (MIN_WEIGHT_KG <= w <= MAX_WEIGHT_KG):
        return None
    if not (MIN_HEIGHT_CM <= h <= MAX_HEIGHT_CM):
        return None
    metres = h / 100.0
    return round(w / (metres * metres), 1)


def _band(value: float, ladder: tuple[tuple[float | None, str], ...]) -> str:
    for upper, code in ladder:
        if upper is None or value < upper:
            return code
    return ladder[-1][1]  # pragma: no cover — the open-ended band always matches


def bmi_band(value: float | None) -> dict | None:
    """Which band a BMI falls in, under BOTH ladders. Pure lookup, no patient involved.

    Returns ``{"bmi", "who", "asia"}`` with band CODES, or None. It deliberately does
    not say what to do about it: that is clinical judgement (rule #2).
    """
    if value is None:
        return None
    return {
        "bmi": value,
        "who": _band(value, _BMI_WHO),
        "asia": _band(value, _BMI_ASIA),
        "source_who": SOURCE_WHO_BMI,
        "source_asia": SOURCE_WHO_BMI_ASIA,
    }


# ---------------------------------------------------------------------------
# Glucose reference
# ---------------------------------------------------------------------------

#: mg/dL per mmol/L for glucose. Both units are in daily use in Bangladeshi labs, so
#: every threshold ships in both rather than making staff convert at the bedside.
MMOL_TO_MGDL = 18.0


def _mgdl(mmol: float) -> int:
    return int(round(mmol * MMOL_TO_MGDL))


def _range(label_en: str, label_bn: str, low_mmol: float | None, high_mmol: float | None) -> dict:
    """One band of one measurement context, in both unit systems.

    ``low``/``high`` are inclusive-lower / inclusive-upper as published; a None end is
    open. Rendering "≥ 7.0" vs "6.1 – 6.9" is the portal's job.
    """
    return {
        "label_en": label_en,
        "label_bn": label_bn,
        "low_mmol_l": low_mmol,
        "high_mmol_l": high_mmol,
        "low_mg_dl": None if low_mmol is None else _mgdl(low_mmol),
        "high_mg_dl": None if high_mmol is None else _mgdl(high_mmol),
    }


#: The whole table. Every context states what it REQUIRES of the sample, because that
#: requirement is the thing that makes the numbers mean anything at all.
_GLUCOSE_CONTEXTS: tuple[dict, ...] = (
    {
        "code": "fasting",
        "name_en": "Fasting plasma glucose",
        "name_bn": "খালি পেটে রক্তের গ্লুকোজ",
        "requires_context_en": "No calorie intake for at least 8 hours. A 'fasting' value from a patient who ate is not a fasting value.",
        "requires_context_bn": "কমপক্ষে ৮ ঘণ্টা কিছু খাওয়া যাবে না। রোগী খেয়ে থাকলে সেটি খালি পেটের মান নয়।",
        "source": SOURCE_WHO_DIABETES,
        "bands": (
            _range("Normal", "স্বাভাবিক", None, 6.0),
            _range("Impaired fasting glucose (WHO)", "খালি পেটে ব্যাহত গ্লুকোজ (WHO)", 6.1, 6.9),
            _range("Diabetes threshold", "ডায়াবেটিসের সীমা", 7.0, None),
        ),
        # The one place two standards disagree — surfaced, never silently resolved.
        "note_en": "The ADA places the lower bound of the impaired band at 5.6 mmol/L (100 mg/dL), not 6.1. A value between 5.6 and 6.1 is therefore classified differently by the two standards — which is exactly why the number alone is not a finding.",
        "note_bn": "ADA অনুযায়ী ব্যাহত মাত্রার নিচের সীমা ৬.১ নয়, ৫.৬ mmol/L (১০০ mg/dL)। তাই ৫.৬–৬.১ এর মধ্যে একটি মান দুই মানদণ্ডে ভিন্নভাবে গণ্য হয় — এজন্যই শুধু সংখ্যা দিয়ে সিদ্ধান্ত নেওয়া যায় না।",
        "note_source": SOURCE_ADA,
    },
    {
        "code": "ogtt_2h",
        "name_en": "2-hour plasma glucose (75 g OGTT)",
        "name_bn": "২ ঘণ্টা পর রক্তের গ্লুকোজ (৭৫ গ্রাম OGTT)",
        "requires_context_en": "Measured exactly 2 hours after a standard 75 g oral glucose load. A casual post-meal sample is NOT this test.",
        "requires_context_bn": "৭৫ গ্রাম গ্লুকোজ খাওয়ার ঠিক ২ ঘণ্টা পর মাপা। সাধারণ খাবারের পরের নমুনা এই পরীক্ষা নয়।",
        "source": SOURCE_WHO_DIABETES,
        "bands": (
            _range("Normal", "স্বাভাবিক", None, 7.7),
            _range("Impaired glucose tolerance", "গ্লুকোজ সহনশীলতা ব্যাহত", 7.8, 11.0),
            _range("Diabetes threshold", "ডায়াবেটিসের সীমা", 11.1, None),
        ),
        "note_en": None,
        "note_bn": None,
        "note_source": None,
    },
    {
        "code": "random",
        "name_en": "Random / casual plasma glucose",
        "name_bn": "যেকোনো সময়ের রক্তের গ্লুকোজ",
        "requires_context_en": "Any time of day, regardless of meals. On its own it can only RAISE a question — it establishes nothing without symptoms plus confirmation.",
        "requires_context_bn": "দিনের যেকোনো সময়, খাওয়ার সাথে সম্পর্ক ছাড়াই। একা এই মান শুধু প্রশ্ন তোলে — উপসর্গ ও নিশ্চিতকরণ ছাড়া কিছুই প্রমাণ করে না।",
        "source": SOURCE_WHO_DIABETES,
        "bands": (
            _range("Below the threshold", "সীমার নিচে", None, 11.0),
            _range("Diabetes threshold, WITH symptoms", "ডায়াবেটিসের সীমা, উপসর্গসহ", 11.1, None),
        ),
        "note_en": "≥ 11.1 mmol/L supports diabetes only together with classic symptoms; without symptoms it must be confirmed by a fasting or OGTT value on a separate day.",
        "note_bn": "≥ ১১.১ mmol/L কেবল সাধারণ উপসর্গসহ থাকলেই ডায়াবেটিস নির্দেশ করে; উপসর্গ না থাকলে অন্য দিনে খালি পেটে বা OGTT দিয়ে নিশ্চিত করতে হবে।",
        "note_source": SOURCE_WHO_DIABETES,
    },
    {
        "code": "hba1c",
        "name_en": "HbA1c (glycated haemoglobin)",
        "name_bn": "HbA1c (গ্লাইকেটেড হিমোগ্লোবিন)",
        "requires_context_en": "Reflects roughly the last 2-3 months. Unreliable in anaemia, haemoglobinopathy, pregnancy, recent transfusion or chronic kidney disease — all common here.",
        "requires_context_bn": "গত ২-৩ মাসের গড় নির্দেশ করে। রক্তাল্পতা, হিমোগ্লোবিনের রোগ, গর্ভাবস্থা, সাম্প্রতিক রক্ত সঞ্চালন বা কিডনি রোগে নির্ভরযোগ্য নয় — যা এখানে সাধারণ।",
        "source": SOURCE_WHO_HBA1C,
        "bands": (
            {"label_en": "Normal", "label_bn": "স্বাভাবিক",
             "low_percent": None, "high_percent": 5.6},
            {"label_en": "Increased risk", "label_bn": "ঝুঁকি বেড়েছে",
             "low_percent": 5.7, "high_percent": 6.4},
            {"label_en": "Diabetes threshold", "label_bn": "ডায়াবেটিসের সীমা",
             "low_percent": 6.5, "high_percent": None},
        ),
        "note_en": "6.5% corresponds to 48 mmol/mol in IFCC units.",
        "note_bn": "৬.৫% মানে IFCC এককে ৪৮ mmol/mol।",
        "note_source": SOURCE_WHO_HBA1C,
    },
)


#: S39 (ADR-0064) — the contexts a medic may RECORD a reading against. A subset of
#: the chart on purpose: HbA1c is a percentage, not mmol/L, and is a laboratory
#: result rather than the bedside reading taken at intake, so it stays a reference row
#: with no input beside it. Kept here, next to the chart itself, so the storable set
#: can never drift from the published set it is a subset of.
RECORDABLE_GLUCOSE_CONTEXTS: tuple[str, ...] = ("fasting", "ogtt_2h", "random")


def glucose_reference() -> dict:
    """The full glucose reference chart. Takes NO patient value, by design.

    A function that accepted a reading and returned a band would be one refactor away
    from printing "Diabetes" beside a patient's name. The chart is displayed; a person
    reads their own measurement against it.
    """
    return {
        "contexts": [dict(c, bands=list(c["bands"])) for c in _GLUCOSE_CONTEXTS],
        "recordable": list(RECORDABLE_GLUCOSE_CONTEXTS),
        "disclaimer": REFERENCE_DISCLAIMER,
        "disclaimer_bn": REFERENCE_DISCLAIMER_BN,
    }


# ---------------------------------------------------------------------------
# Diagnostic test vocabulary (B4)
# ---------------------------------------------------------------------------

#: (canonical English name, Bangla name, group, common aliases the doctor may type).
#:
#: Scope is deliberate: the investigations actually ordered from a Bangladeshi
#: outpatient clinic, written the way they are written on a local prescription pad
#: ("CBC", "Urine R/M/E", "USG of whole abdomen", "Widal test"). It is a TYPING AID and
#: nothing more — the doctor can always type a test that is not on it, and selecting one
#: orders nothing (the brief: *"Suggestions are assistance, not automatic orders"*).
_TESTS: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    # Haematology
    ("CBC with ESR", "সিবিসি ও ইএসআর", "haematology", ("cbc", "complete blood count", "blood count", "esr")),
    ("Haemoglobin (Hb%)", "হিমোগ্লোবিন", "haematology", ("hb", "haemoglobin", "hemoglobin")),
    ("Peripheral blood film", "পেরিফেরাল ব্লাড ফিল্ম", "haematology", ("pbf", "blood film")),
    ("Platelet count", "প্লেটলেট কাউন্ট", "haematology", ("platelet",)),
    ("Prothrombin time (PT/INR)", "প্রোথ্রম্বিন টাইম", "haematology", ("pt", "inr")),
    ("Blood grouping & Rh typing", "রক্তের গ্রুপ ও আরএইচ", "haematology", ("blood group", "grouping")),
    # Diabetes / metabolic
    ("Fasting blood sugar (FBS)", "খালি পেটে রক্তের সুগার", "metabolic", ("fbs", "fasting sugar", "fasting glucose")),
    ("2 hours after breakfast blood sugar", "নাস্তার ২ ঘণ্টা পর রক্তের সুগার", "metabolic", ("2habf", "post prandial", "pp sugar")),
    ("Random blood sugar (RBS)", "যেকোনো সময়ের রক্তের সুগার", "metabolic", ("rbs", "random sugar")),
    ("HbA1c", "এইচবিএ১সি", "metabolic", ("hba1c", "glycated haemoglobin", "a1c")),
    ("OGTT (75 g)", "ওজিটিটি", "metabolic", ("ogtt", "glucose tolerance")),
    ("Fasting lipid profile", "লিপিড প্রোফাইল", "metabolic", ("lipid", "cholesterol", "triglyceride")),
    ("Serum uric acid", "সিরাম ইউরিক অ্যাসিড", "metabolic", ("uric acid",)),
    # Organ function
    ("Serum creatinine", "সিরাম ক্রিয়েটিনিন", "biochemistry", ("creatinine", "s creatinine")),
    ("Blood urea", "রক্তের ইউরিয়া", "biochemistry", ("urea",)),
    ("Serum electrolytes", "সিরাম ইলেক্ট্রোলাইট", "biochemistry", ("electrolytes", "na k cl")),
    ("Liver function test (LFT)", "লিভার ফাংশন টেস্ট", "biochemistry", ("lft", "liver function", "sgpt", "alt")),
    ("Serum bilirubin", "সিরাম বিলিরুবিন", "biochemistry", ("bilirubin",)),
    ("Thyroid function test (TSH, FT4)", "থাইরয়েড ফাংশন টেস্ট", "biochemistry", ("tsh", "thyroid", "ft4")),
    ("Serum calcium", "সিরাম ক্যালসিয়াম", "biochemistry", ("calcium",)),
    ("Serum vitamin D (25-OH)", "সিরাম ভিটামিন ডি", "biochemistry", ("vitamin d", "vit d")),
    ("Serum ferritin", "সিরাম ফেরিটিন", "biochemistry", ("ferritin",)),
    # Urine / stool
    ("Urine R/M/E", "প্রস্রাবের রুটিন পরীক্ষা", "urine", ("urine", "urine routine", "rme", "urine r/e")),
    ("Urine C/S", "প্রস্রাবের কালচার", "urine", ("urine culture", "c/s", "culture sensitivity")),
    ("Urine ACR (albumin/creatinine)", "প্রস্রাবের এসিআর", "urine", ("acr", "microalbumin")),
    ("Stool R/M/E", "মলের রুটিন পরীক্ষা", "stool", ("stool", "stool routine")),
    ("Stool occult blood", "মলে গুপ্ত রক্ত", "stool", ("occult blood", "fob")),
    # Infection
    ("Dengue NS1 antigen", "ডেঙ্গু NS1 এন্টিজেন", "infection", ("ns1", "dengue")),
    ("Dengue IgG / IgM", "ডেঙ্গু IgG / IgM", "infection", ("dengue igg", "dengue igm")),
    ("Widal test", "উইডাল টেস্ট", "infection", ("widal", "typhoid")),
    ("Blood culture & sensitivity", "রক্তের কালচার", "infection", ("blood culture",)),
    ("ICT for malaria", "ম্যালেরিয়ার আইসিটি", "infection", ("malaria", "mp", "ict malaria")),
    ("Mantoux test (MT)", "ম্যানটু টেস্ট", "infection", ("mantoux", "mt", "tuberculin")),
    ("Sputum for AFB", "কফে এএফবি", "infection", ("afb", "sputum")),
    ("HBsAg", "এইচবিএসএজি", "infection", ("hbsag", "hepatitis b")),
    ("Anti-HCV", "এন্টি-এইচসিভি", "infection", ("hcv", "hepatitis c")),
    ("CRP", "সিআরপি", "infection", ("crp", "c reactive protein")),
    # Imaging / cardiac
    ("Chest X-ray P/A view", "বুকের এক্স-রে", "imaging", ("cxr", "chest x ray", "x-ray chest")),
    ("X-ray of the affected part", "আক্রান্ত স্থানের এক্স-রে", "imaging", ("x-ray", "xray")),
    ("USG of whole abdomen", "পেটের আল্ট্রাসনোগ্রাম", "imaging", ("usg", "ultrasound", "ultrasonogram", "abdomen usg")),
    ("USG of the pregnancy profile", "গর্ভাবস্থার আল্ট্রাসনোগ্রাম", "imaging", ("pregnancy profile", "obstetric usg")),
    ("CT scan", "সিটি স্ক্যান", "imaging", ("ct", "ct scan")),
    ("MRI", "এমআরআই", "imaging", ("mri",)),
    ("ECG", "ইসিজি", "cardiac", ("ecg", "ekg", "electrocardiogram")),
    ("Echocardiogram", "ইকোকার্ডিওগ্রাম", "cardiac", ("echo", "echocardiography")),
    ("Exercise tolerance test (ETT)", "ইটিটি", "cardiac", ("ett", "treadmill", "exercise test")),
    ("Troponin I", "ট্রপোনিন আই", "cardiac", ("troponin",)),
    # Other
    ("Spirometry", "স্পাইরোমেট্রি", "other", ("spirometry", "lung function", "pft")),
    ("Endoscopy of upper GI tract", "আপার জিআই এন্ডোস্কোপি", "other", ("endoscopy", "ugie")),
    ("Pregnancy test (urine hCG)", "গর্ভধারণ পরীক্ষা", "other", ("pregnancy test", "hcg", "upt")),
)


def test_vocabulary() -> list[dict]:
    """The suggestion list, as plain dicts. Stable order — the UI filters, never sorts."""
    return [
        {"name_en": en, "name_bn": bn, "group": group, "aliases": list(aliases)}
        for en, bn, group, aliases in _TESTS
    ]


def search_tests(query: str, *, limit: int = 8) -> list[dict]:
    """Substring match over name and aliases, prefix matches ranked first.

    Server-side so the SAME matching serves the portal, a future mobile client and the
    tests. An empty query returns the head of the list rather than nothing, so the field
    can show suggestions before a doctor has typed anything.
    """
    entries = test_vocabulary()
    text = str(query or "").strip().lower()
    if not text:
        return entries[:limit]
    exact_prefix: list[dict] = []
    contains: list[dict] = []
    for entry in entries:
        haystacks = [entry["name_en"].lower(), entry["name_bn"]] + entry["aliases"]
        if any(h.startswith(text) for h in haystacks):
            exact_prefix.append(entry)
        elif any(text in h for h in haystacks):
            contains.append(entry)
    return (exact_prefix + contains)[:limit]
