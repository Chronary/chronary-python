from __future__ import annotations

import json

import httpx
import pytest
import respx

from chronary import (
    AsyncChronary,
    BillingSummary,
    Chronary,
    PermissionDeniedError,
    PlanRequiredError,
    QuotaExceededError,
    RateLimitError,
    UpgradeRequest,
)

BASE = "https://api.chronary.ai"

REQUEST = {
    "id": "upr_abc123",
    "status": "pending",
    "plan": "pro",
    "interval": "month",
    "reason": "Hit the event limit",
    "feature": None,
    "metric": "events",
    "requested_via": "api",
    "requested_by_key_prefix": "chr_sk_abcdefghijkl",
    "approval_url": "https://console.test/settings/billing/requests/upr_abc123",
    "created_at": "2026-10-19T00:00:00.000Z",
    "expires_at": "2026-10-26T00:00:00.000Z",
    "completed_at": None,
    "declined_at": None,
    "canceled_at": None,
}

SUMMARY = {
    "plan": "free",
    "plan_source": None,
    "plan_expires_at": None,
    "status": None,
    "interval": None,
    "current_period_end": None,
    "cancel_at": None,
    "cancel_at_period_end": False,
    "renews_at": None,
    "price": None,
    "has_billing_account": False,
    "self_serve_upgrade": True,
    "upgrade_options": [
        {"plan": "pro", "interval": "month", "amount": 2900, "currency": "usd", "savings_vs_monthly": 0}
    ],
    "upgrade_url": "https://console.test/settings/billing",
    "manage_url": "https://console.test/settings/billing",
    "contact_url": None,
    "pending_upgrade_request": REQUEST,
    "offer": None,
    "past_due": None,
    "credit": None,
}


@respx.mock
def test_sync_billing_get() -> None:
    route = respx.get(f"{BASE}/v1/billing").mock(return_value=httpx.Response(200, json=SUMMARY))
    with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
        summary = client.billing.get()
    assert isinstance(summary, BillingSummary)
    assert summary.plan == "free"
    assert summary.upgrade_options[0].amount == 2900
    assert summary.pending_upgrade_request is not None
    assert summary.pending_upgrade_request.id == "upr_abc123"
    assert route.called


@respx.mock
def test_sync_billing_get_past_due() -> None:
    past_due = {
        "amount_due": 1581,
        "currency": "usd",
        "failed_at": "2026-10-23T00:00:00.000Z",
        "next_payment_attempt": None,
        "hosted_invoice_url": "https://invoice.test/pay",
        "attempt_count": 4,
    }
    respx.get(f"{BASE}/v1/billing").mock(
        return_value=httpx.Response(200, json={**SUMMARY, "status": "past_due", "past_due": past_due})
    )
    with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
        summary = client.billing.get()
    assert summary.past_due is not None
    assert summary.past_due.amount_due == 1581
    assert summary.past_due.next_payment_attempt is None


@respx.mock
def test_sync_billing_get_credit() -> None:
    respx.get(f"{BASE}/v1/billing").mock(
        return_value=httpx.Response(200, json={**SUMMARY, "credit": {"amount": 26100, "currency": "usd"}})
    )
    with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
        summary = client.billing.get()
    assert summary.credit is not None
    assert summary.credit.amount == 26100
    assert summary.credit.currency == "usd"


@respx.mock
def test_sync_upgrade_request_lifecycle() -> None:
    create = respx.post(f"{BASE}/v1/billing/upgrade-requests").mock(
        return_value=httpx.Response(201, json={**REQUEST, "owner_notification": "queued", "reused": False})
    )
    respx.get(f"{BASE}/v1/billing/upgrade-requests/upr_abc123").mock(
        return_value=httpx.Response(200, json={**REQUEST, "status": "completed", "approval_url": None})
    )
    respx.post(f"{BASE}/v1/billing/upgrade-requests/upr_abc123/cancel").mock(
        return_value=httpx.Response(200, json={**REQUEST, "status": "canceled"})
    )
    with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
        req = client.billing.upgrade_requests.create(
            interval="year", reason="Need more", metric="events", idempotency_key="idem-123"
        )
        assert isinstance(req, UpgradeRequest)
        assert req.approval_url is not None
        assert req.owner_notification == "queued"
        assert client.billing.upgrade_requests.get("upr_abc123").status == "completed"
        assert client.billing.upgrade_requests.cancel("upr_abc123").status == "canceled"

    sent = create.calls[0].request
    assert sent.headers["Idempotency-Key"] == "idem-123"
    assert json.loads(sent.content) == {"interval": "year", "reason": "Need more", "metric": "events"}


@respx.mock
def test_sync_upgrade_request_create_defaults() -> None:
    create = respx.post(f"{BASE}/v1/billing/upgrade-requests").mock(
        return_value=httpx.Response(200, json={**REQUEST, "reused": True})
    )
    with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
        req = client.billing.upgrade_requests.create()
    assert req.reused is True
    sent = create.calls[0].request
    assert json.loads(sent.content) == {}
    assert sent.headers["Idempotency-Key"]


@pytest.mark.asyncio
@respx.mock
async def test_async_billing_and_upgrade_requests() -> None:
    respx.get(f"{BASE}/v1/billing").mock(return_value=httpx.Response(200, json=SUMMARY))
    create = respx.post(f"{BASE}/v1/billing/upgrade-requests").mock(
        return_value=httpx.Response(201, json=REQUEST)
    )
    respx.get(f"{BASE}/v1/billing/upgrade-requests/upr_abc123").mock(
        return_value=httpx.Response(200, json=REQUEST)
    )
    respx.post(f"{BASE}/v1/billing/upgrade-requests/upr_abc123/cancel").mock(
        return_value=httpx.Response(200, json={**REQUEST, "status": "canceled"})
    )
    async with AsyncChronary(api_key="chr_sk_x", base_url=BASE) as client:
        assert (await client.billing.get()).plan == "free"
        req = await client.billing.upgrade_requests.create(reason="r", idempotency_key="k1")
        assert req.id == "upr_abc123"
        assert (await client.billing.upgrade_requests.get("upr_abc123")).status == "pending"
        assert (await client.billing.upgrade_requests.cancel("upr_abc123")).status == "canceled"
    assert create.calls[0].request.headers["Idempotency-Key"] == "k1"


@respx.mock
def test_plan_required_error_exposes_upgrade_fields() -> None:
    body = {
        "error": {
            "type": "plan_required",
            "message": "Pro required",
            "request_id": "req_1",
            "required_plan": "pro",
            "feature": "scoped_keys",
            "upgrade_url": "https://console.test/settings/billing",
            "docs_url": "https://docs.test/plans",
            "contact_url": "https://chronary.ai/contact",
        }
    }
    respx.get(f"{BASE}/v1/billing").mock(return_value=httpx.Response(403, json=body))
    with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
        with pytest.raises(PlanRequiredError) as exc_info:
            client.billing.get()
    err = exc_info.value
    assert isinstance(err, PermissionDeniedError)
    assert err.status_code == 403
    assert err.upgrade_url == "https://console.test/settings/billing"
    assert err.docs_url == "https://docs.test/plans"
    assert err.required_plan == "pro"
    assert err.feature == "scoped_keys"
    assert err.contact_url == "https://chronary.ai/contact"
    assert err.body == body


@respx.mock
def test_other_403_stays_permission_denied() -> None:
    body = {"error": {"type": "forbidden", "message": "Only org-level API keys can access this resource", "request_id": "r"}}
    respx.get(f"{BASE}/v1/billing").mock(return_value=httpx.Response(403, json=body))
    with Chronary(api_key="chr_ak_x", base_url=BASE) as client:
        with pytest.raises(PermissionDeniedError) as exc_info:
            client.billing.get()
    assert not isinstance(exc_info.value, PlanRequiredError)
    assert exc_info.value.upgrade_url is None


@respx.mock
def test_quota_exceeded_exposes_metric_limit_upgrade_url() -> None:
    body = {
        "error": {
            "type": "quota_exceeded",
            "message": "Quota hit",
            "request_id": "req_2",
            "metric": "api_calls",
            "limit": 50000,
            "upgrade_url": "https://console.test/settings/billing",
        }
    }
    respx.get(f"{BASE}/v1/billing").mock(return_value=httpx.Response(429, json=body))
    with Chronary(api_key="chr_sk_x", base_url=BASE, max_retries=0) as client:
        with pytest.raises(QuotaExceededError) as exc_info:
            client.billing.get()
    err = exc_info.value
    assert err.status_code == 429
    assert err.metric == "api_calls"
    assert err.limit == 50000
    assert err.upgrade_url == "https://console.test/settings/billing"
    assert not isinstance(err, RateLimitError)


@respx.mock
def test_developer_plan_fields() -> None:
    respx.get(f"{BASE}/v1/billing").mock(
        return_value=httpx.Response(
            200,
            json={
                **SUMMARY,
                "plan": "pro",
                "pending_plan": "developer",
                "pending_plan_interval": "month",
                "pending_plan_at": "2026-12-01T00:00:00Z",
                "upgrade_options": [
                    {
                        "plan": "developer",
                        "interval": "month",
                        "amount": 900,
                        "currency": "usd",
                        "savings_vs_monthly": 0,
                        "via": "switch_plan",
                    }
                ],
            },
        )
    )
    with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
        summary = client.billing.get()
    assert summary.pending_plan == "developer"
    assert summary.pending_plan_interval == "month"
    assert summary.pending_plan_at == "2026-12-01T00:00:00Z"
    assert summary.upgrade_options[0].plan == "developer"
    assert summary.upgrade_options[0].via == "switch_plan"


@respx.mock
def test_plans_accept_developer_and_unknown_ids() -> None:
    plan = {
        "name": "X",
        "tagline": "t",
        "price": 900,
        "currency": "usd",
        "annual_price": 9000,
        "limits": None,
        "display_features": [],
        "recommended": False,
    }
    respx.get(f"{BASE}/v1/plans").mock(
        return_value=httpx.Response(
            200, json={"plans": [{**plan, "id": "developer"}, {**plan, "id": "some_future_plan"}]}
        )
    )
    with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
        resp = client.plans.list()
    assert [p.id for p in resp.plans] == ["developer", "some_future_plan"]
    assert resp.plans[0].annual_price == 9000


@respx.mock
def test_quota_error_exposes_upgrade_plan() -> None:
    body = {
        "error": {
            "type": "quota_exceeded",
            "message": "limit",
            "metric": "api_calls",
            "limit": 50000,
            "upgrade_url": "https://console.test/settings/billing",
            "upgrade_plan": "developer",
        }
    }
    respx.get(f"{BASE}/v1/billing").mock(return_value=httpx.Response(429, json=body))
    with Chronary(api_key="chr_sk_x", base_url=BASE) as client:
        with pytest.raises(Exception) as exc_info:
            client.billing.get()
    assert exc_info.value.upgrade_plan == "developer"  # type: ignore[attr-defined]
