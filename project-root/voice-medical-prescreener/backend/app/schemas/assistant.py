"""API data contracts for the M16 doctor drug-info assistant (P3-3).

The disclaimer fields are REQUIRED (not optional) so the contract itself
guarantees no answer ships without them (rule #2).
"""

from pydantic import BaseModel, Field


class DrugInfoRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500,
                          description="The doctor's drug question. Sent to a public "
                                      "web search — must never contain patient data.")


class DrugInfoSource(BaseModel):
    title: str
    url: str
    snippet: str


class DrugInfoOut(BaseModel):
    answer_en: str
    answer_bn: str
    sources: list[DrugInfoSource]
    disclaimer: str
    disclaimer_bn: str
