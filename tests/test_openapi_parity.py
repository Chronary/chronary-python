"""Response-field parity between the OpenAPI spec and the SDK models (#1995).

A field the API documents in a response schema must exist on the matching
model, and a model must not declare a field the spec lacks. Each row maps a
``components.schemas`` name to a model; nested object properties are checked
against the nested model's fields too. Add a row to cover another response.

The spec lives in the monorepo (``apps/api/openapi.json``); the public SDK
mirror has no ``apps/api``, so the module is skipped there.
"""

from __future__ import annotations

import json
import typing
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from chronary import UsageResponse

SPEC_PATH = Path(__file__).resolve().parents[3] / "apps" / "api" / "openapi.json"

if not SPEC_PATH.is_file():
    pytest.skip("apps/api/openapi.json not present (public mirror)", allow_module_level=True)

SCHEMAS: dict[str, Any] = json.loads(SPEC_PATH.read_text(encoding="utf-8"))["components"][
    "schemas"
]

PARITY: list[tuple[str, type[BaseModel]]] = [
    ("Usage", UsageResponse),
]


def _nested_model(model: type[BaseModel], field: str) -> type[BaseModel] | None:
    annotation = model.model_fields[field].annotation
    candidates = typing.get_args(annotation) or (annotation,)
    for candidate in candidates:
        if isinstance(candidate, type) and issubclass(candidate, BaseModel):
            return candidate
    return None


@pytest.mark.parametrize(("schema_name", "model"), PARITY, ids=[name for name, _ in PARITY])
def test_top_level_fields_match_spec(schema_name: str, model: type[BaseModel]) -> None:
    spec_fields = set(SCHEMAS[schema_name]["properties"])
    assert sorted(model.model_fields) == sorted(spec_fields)


@pytest.mark.parametrize(("schema_name", "model"), PARITY, ids=[name for name, _ in PARITY])
def test_nested_fields_match_spec(schema_name: str, model: type[BaseModel]) -> None:
    for name, prop in SCHEMAS[schema_name]["properties"].items():
        nested_props = prop.get("properties")
        if not nested_props:
            continue
        nested = _nested_model(model, name)
        assert nested is not None, f"{schema_name}.{name} is an object in the spec, not a model"
        assert (name, sorted(nested.model_fields)) == (name, sorted(nested_props))
