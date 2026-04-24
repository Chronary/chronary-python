from __future__ import annotations

from typing import Any, Literal

from typing_extensions import NotRequired, Required, TypedDict

from .._models import ChronaryModel
from .._resource import AsyncAPIResource, SyncAPIResource

FeedbackType = Literal["bug", "feature", "friction"]


class FeedbackSubmitParams(TypedDict):
    type: Required[FeedbackType]
    message: Required[str]
    context: NotRequired[dict[str, Any]]


class FeedbackAcceptedResponse(ChronaryModel):
    """Response returned when feedback is accepted for triage."""

    status: Literal["accepted"]


_FEEDBACK_PATH = "/v1/feedback"


class Feedback(SyncAPIResource):
    """client.feedback -- submit structured feedback to Chronary."""

    def submit(
        self,
        *,
        type: FeedbackType,
        message: str,
        context: dict[str, Any] | None = None,
        max_retries: int | None = None,
    ) -> FeedbackAcceptedResponse:
        body: dict[str, Any] = {"type": type, "message": message}
        if context is not None:
            body["context"] = context
        resp = self._request("POST", _FEEDBACK_PATH, json=body, max_retries=max_retries)
        return self._build(FeedbackAcceptedResponse, resp)


class AsyncFeedback(AsyncAPIResource):
    """client.feedback -- async submit structured feedback to Chronary."""

    async def submit(
        self,
        *,
        type: FeedbackType,
        message: str,
        context: dict[str, Any] | None = None,
        max_retries: int | None = None,
    ) -> FeedbackAcceptedResponse:
        body: dict[str, Any] = {"type": type, "message": message}
        if context is not None:
            body["context"] = context
        resp = await self._request(
            "POST", _FEEDBACK_PATH, json=body, max_retries=max_retries
        )
        return self._build(FeedbackAcceptedResponse, resp)
