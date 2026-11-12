from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import httpx


class ChronaryError(Exception):
    """Base exception for all Chronary SDK errors."""


class APIError(ChronaryError):
    """Base class for API-related errors."""

    message: str
    request: httpx.Request | None
    body: Any

    def __init__(
        self,
        message: str,
        *,
        request: httpx.Request | None = None,
        body: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.request = request
        self.body = body


class APIConnectionError(APIError):
    """Raised when a connection to the API cannot be established."""

    def __init__(
        self,
        message: str = "Connection error.",
        *,
        request: httpx.Request | None = None,
    ) -> None:
        super().__init__(message, request=request)


class APITimeoutError(APIConnectionError):
    """Raised when a request times out."""

    def __init__(
        self,
        message: str = "Request timed out.",
        *,
        request: httpx.Request | None = None,
    ) -> None:
        super().__init__(message, request=request)


class APIStatusError(APIError):
    """Raised when the API returns a non-success status code."""

    response: httpx.Response
    status_code: int
    request_id: str | None
    error_type: str | None
    param: str | None
    # Plan / quota guidance fields (present on plan_required and quota_exceeded errors).
    upgrade_url: str | None
    docs_url: str | None
    required_plan: str | None
    # Self-serve plan `upgrade_url` leads to: the next plan up (quota_exceeded and count caps).
    upgrade_plan: str | None
    feature: str | None
    contact_url: str | None
    metric: str | None
    limit: int | None

    def __init__(
        self,
        message: str,
        *,
        response: httpx.Response,
        body: Any = None,
    ) -> None:
        request = response.request
        super().__init__(message, request=request, body=body)
        self.response = response
        self.status_code = response.status_code

        error_obj = body.get("error", {}) if isinstance(body, dict) else {}
        self.request_id = error_obj.get("request_id")
        self.error_type = error_obj.get("type")
        self.param = error_obj.get("param")
        self.upgrade_url = error_obj.get("upgrade_url")
        self.docs_url = error_obj.get("docs_url")
        self.required_plan = error_obj.get("required_plan")
        self.upgrade_plan = error_obj.get("upgrade_plan")
        self.feature = error_obj.get("feature")
        self.contact_url = error_obj.get("contact_url")
        self.metric = error_obj.get("metric")
        self.limit = error_obj.get("limit")


class BadRequestError(APIStatusError):
    """400 — validation_error"""


class AuthenticationError(APIStatusError):
    """401 — authentication_error"""


class PermissionDeniedError(APIStatusError):
    """403 — forbidden"""


class PlanRequiredError(PermissionDeniedError):
    """403 — plan_required (feature not included in the current plan)"""


class NotFoundError(APIStatusError):
    """404 — not_found"""


class RateLimitError(APIStatusError):
    """429 — rate_limit_error"""


class QuotaExceededError(APIStatusError):
    """429 — quota_exceeded"""


class InternalServerError(APIStatusError):
    """500+ — internal_error"""


_STATUS_CODE_MAP: dict[int, type[APIStatusError]] = {
    400: BadRequestError,
    401: AuthenticationError,
    403: PermissionDeniedError,
    404: NotFoundError,
    500: InternalServerError,
}


def _make_status_error(response: httpx.Response, body: Any) -> APIStatusError:
    """Build the appropriate exception from an HTTP error response."""
    error_obj = body.get("error", {}) if isinstance(body, dict) else {}
    message = error_obj.get("message", f"Error code: {response.status_code}")

    if response.status_code == 429:
        error_type = error_obj.get("type", "")
        if error_type == "quota_exceeded":
            return QuotaExceededError(message, response=response, body=body)
        return RateLimitError(message, response=response, body=body)

    if response.status_code == 403 and error_obj.get("type") == "plan_required":
        return PlanRequiredError(message, response=response, body=body)

    cls = _STATUS_CODE_MAP.get(response.status_code)
    if cls is None:
        cls = InternalServerError if response.status_code >= 500 else APIStatusError

    return cls(message, response=response, body=body)
