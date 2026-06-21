"""API data contract for generated document exports."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, computed_field


class DocumentOut(BaseModel):
    """A generated export file as returned by the API (metadata only)."""

    model_config = ConfigDict(from_attributes=True)  # build from ORM objects

    id: str
    utterance_id: int
    kind: str  # "raw" | "corrected" (or "combined" for legacy rows)
    format: str
    filename: str
    created_at: datetime

    @computed_field  # included in the JSON response so the UI can link directly
    @property
    def download_url(self) -> str:
        return f"/api/documents/{self.id}/download"
