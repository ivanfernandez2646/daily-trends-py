from typing import Any, cast

from fastapi import FastAPI


class CmsBackendApi(FastAPI):
    """The app, with an OpenAPI document that describes the error contract it really has."""

    # `Any` comes from the signature FastAPI declares for the document.
    def openapi(self) -> dict[str, Any]:
        if self.openapi_schema is None:
            self.openapi_schema = _without_validation_errors(super().openapi())
        return self.openapi_schema


def _without_validation_errors(document: dict[str, Any]) -> dict[str, Any]:
    """Drop the 422 FastAPI adds to every operation: a validation error answers 400 here."""
    paths = cast(dict[str, dict[str, dict[str, object]]], document.get("paths", {}))
    for operations in paths.values():
        for operation in operations.values():
            cast(dict[str, object], operation.get("responses", {})).pop("422", None)
    components = cast(dict[str, dict[str, object]], document.get("components", {}))
    for name in ("HTTPValidationError", "ValidationError"):
        components.get("schemas", {}).pop(name, None)
    return document
