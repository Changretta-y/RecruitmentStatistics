"""Safe API exception responses with no implementation details."""

from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


_SENSITIVE_KEYS = {"password", "password_hash", "token", "access", "refresh", "authorization", "traceback", "sql"}


def _safe_value(value, key: str | None = None):
    if key and any(marker in key.lower() for marker in _SENSITIVE_KEYS):
        return "[redacted]"
    if isinstance(value, dict):
        return {str(child_key): _safe_value(child_value, str(child_key)) for child_key, child_value in value.items()}
    if isinstance(value, list):
        return [_safe_value(item) for item in value]
    if isinstance(value, tuple):
        return [_safe_value(item) for item in value]
    if isinstance(value, str):
        lowered = value.lower()
        if "traceback" in lowered or "stack trace" in lowered or "syntax error at or near" in lowered:
            return "Request could not be processed."
    return value


def safe_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return Response(
            {"code": "INTERNAL_ERROR", "detail": "Request could not be processed."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    response.data = _safe_value(response.data)
    return response
