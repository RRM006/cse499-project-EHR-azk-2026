"""API data contracts for the M16 doctor drug-info assistant (P3-3).

The disclaimer fields are REQUIRED (not optional) so the contract itself
guarantees no answer ships without them (rule #2).
"""

from pydantic import BaseModel, Field


class DrugInfoRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500,
                          description="The doctor's question about a medicine or a "
                                      "diagnostic test. Sent to a public web search — "
                                      "must never contain patient data.")
    #: S38 (B6). Opt-IN, and off by default, so a general question ("what is
    #: metformin?") ships no patient data anywhere at all. When true, the LLM — never
    #: the web search — additionally receives this visit's DE-IDENTIFIED picture
    #: (age, sex, body area, vitals, the derived 10 fields). Never the name, the phone
    #: number or the raw transcript.
    use_case_context: bool = Field(
        False,
        description="Include this visit's de-identified clinical summary in the prompt "
                    "so the assistant can answer 'which tests might be useful for this "
                    "patient?'. Never sent to the web search.",
    )


class DrugInfoSource(BaseModel):
    title: str
    url: str
    snippet: str


class DrugInfoOut(BaseModel):
    answer_en: str
    answer_bn: str
    sources: list[DrugInfoSource]
    #: S38 (B6): test names the assistant put forward, as a plain list the doctor may
    #: CLICK to insert into the Required Tests field they are writing. Nothing is
    #: ordered by their presence here — an order exists only once a human generates a
    #: prescription (rule #2, and the brief's "never automatically order a test").
    suggested_tests: list[str] = Field(
        default_factory=list,
        description="Advisory test names. Insertable by the doctor; never auto-ordered.",
    )
    disclaimer: str
    disclaimer_bn: str
    #: Set when the server's output guard judged the reply to read as a patient-specific
    #: instruction. The answer is still returned — hiding what the model said would be
    #: worse — but the disclaimer above is replaced with a stronger one.
    flagged_reason: str | None = Field(
        None, description="Machine reason the answer was flagged, or null."
    )
    used_case_context: bool = Field(
        False, description="Whether the patient's de-identified summary was in the prompt."
    )
