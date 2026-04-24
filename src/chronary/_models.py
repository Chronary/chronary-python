from __future__ import annotations

from pydantic import BaseModel, ConfigDict, PrivateAttr


class ChronaryModel(BaseModel):
    """Base model for all Chronary API response objects."""

    model_config = ConfigDict(
        extra="allow",
        frozen=True,
        populate_by_name=True,
    )

    _request_id: str | None = PrivateAttr(default=None)
