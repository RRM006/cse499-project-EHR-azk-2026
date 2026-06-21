"""API data contract for generated document exports."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    """A generated export file as returned by the API (metadata only)."""

    model_config = ConfigDict(from_attributes=True)  # build from ORM objects

    id: str
    utterance_id: int
    format: str
    filename: str
    created_at: datetime
