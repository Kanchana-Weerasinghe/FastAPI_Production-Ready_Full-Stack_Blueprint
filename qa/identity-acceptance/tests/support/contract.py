"""
Checks responses against the published OpenAPI contract (services/identity/openapi.json).

- Success responses (< 400): the status must be documented and the JSON body must match its schema.
- Error responses (>= 400): the body must be an RFC 9457 Problem Details object with a stable `code`.
"""

import json
from pathlib import Path
from typing import Any

import httpx
from jsonschema import Draft202012Validator

PROBLEM_FIELDS = {"type", "title", "status", "detail", "code"}


class Contract:
    def __init__(self, openapi_path: Path) -> None:
        self.document: dict[str, Any] = json.loads(openapi_path.read_text(encoding="utf-8"))

    def check(self, response: httpx.Response, method: str, path: str) -> None:
        operation = self.document["paths"][path][method.lower()]
        status = str(response.status_code)
        if response.status_code >= 400:
            body = response.json()
            assert response.headers["content-type"].startswith("application/problem+json"), response.headers
            assert PROBLEM_FIELDS <= set(body), f"not a problem-details body: {body}"
            assert body["status"] == response.status_code
            return
        assert status in operation["responses"], f"{method} {path} returned undocumented status {status}"
        content = operation["responses"][status].get("content", {}).get("application/json")
        if content and response.content and response.content != b"null":
            schema = {**content["schema"], "components": self.document.get("components", {})}
            errors = sorted(Draft202012Validator(schema).iter_errors(response.json()), key=str)
            assert not errors, f"{method} {path} {status} does not match the contract: {[e.message for e in errors]}"
