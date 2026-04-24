from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from chronary import Agent

AGENT_JSON = {
    "id": "agt_abc123",
    "name": "Test Agent",
    "type": "ai",
    "description": "A test agent",
    "status": "active",
    "metadata": {"key": "value"},
    "createdAt": "2026-01-15T10:30:00Z",
    "updatedAt": "2026-01-15T12:00:00Z",
}


class TestAgentModel:
    def test_parse_from_camel_case(self) -> None:
        agent = Agent.model_validate(AGENT_JSON)
        assert agent.id == "agt_abc123"
        assert agent.name == "Test Agent"
        assert agent.type == "ai"
        assert agent.description == "A test agent"
        assert agent.status == "active"
        assert agent.metadata == {"key": "value"}
        assert isinstance(agent.created_at, datetime)
        assert isinstance(agent.updated_at, datetime)

    def test_snake_case_access(self) -> None:
        agent = Agent.model_validate(AGENT_JSON)
        assert agent.created_at == datetime(2026, 1, 15, 10, 30, tzinfo=timezone.utc)
        assert agent.updated_at == datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)

    def test_construct_with_snake_case(self) -> None:
        """populate_by_name=True allows snake_case construction."""
        agent = Agent(
            id="agt_x",
            name="X",
            type="human",
            status="active",
            metadata={},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        assert agent.id == "agt_x"

    def test_extra_fields_allowed(self) -> None:
        data = {**AGENT_JSON, "newFutureField": "hello"}
        agent = Agent.model_validate(data)
        assert agent.id == "agt_abc123"
        # Extra field accessible via model_extra
        assert agent.model_extra is not None
        assert agent.model_extra.get("newFutureField") == "hello"

    def test_frozen_immutable(self) -> None:
        agent = Agent.model_validate(AGENT_JSON)
        with pytest.raises(ValidationError):
            agent.name = "Changed"  # type: ignore[misc]

    def test_none_description(self) -> None:
        data = {**AGENT_JSON, "description": None}
        agent = Agent.model_validate(data)
        assert agent.description is None

    def test_serialization_round_trip(self) -> None:
        agent = Agent.model_validate(AGENT_JSON)
        dumped = agent.model_dump(by_alias=True)
        assert "createdAt" in dumped
        assert "updatedAt" in dumped
        agent2 = Agent.model_validate(dumped)
        assert agent2.id == agent.id

    def test_request_id_default_none(self) -> None:
        """Private _request_id attr defaults to None on construction."""
        agent = Agent.model_validate(AGENT_JSON)
        assert agent._request_id is None

    def test_request_id_settable_via_setattr(self) -> None:
        """_request_id can be injected on a frozen model via object.__setattr__."""
        agent = Agent.model_validate(AGENT_JSON)
        object.__setattr__(agent, "_request_id", "req_abc123")
        assert agent._request_id == "req_abc123"

    def test_request_id_excluded_from_dump(self) -> None:
        """Private attrs must not leak into model_dump output."""
        agent = Agent.model_validate(AGENT_JSON)
        object.__setattr__(agent, "_request_id", "req_abc123")
        dumped = agent.model_dump()
        assert "_request_id" not in dumped
        assert "request_id" not in dumped
