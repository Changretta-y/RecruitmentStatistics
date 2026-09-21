"""Security middleware for CORS policy and redacted request audit logs."""

from __future__ import annotations

import logging
import re
import time

from django.conf import settings


request_logger = logging.getLogger("security.request")
_record_id_pattern = re.compile(r"/applications/(\d+)(?:/|$)")


class CorsSecurityMiddleware:
    """Allow only explicitly configured origins; never reflect a wildcard."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        origin = request.headers.get("Origin")
        allowed_origins = set(getattr(settings, "CORS_ALLOWED_ORIGINS", ()))
        if origin and origin in allowed_origins:
            response["Access-Control-Allow-Origin"] = origin
            response["Vary"] = "Origin"
            response["Access-Control-Allow-Credentials"] = "true"
            response["Access-Control-Allow-Methods"] = "GET, POST, PATCH, DELETE, OPTIONS"
            response["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
        return response


class RequestAuditMiddleware:
    """Log request metadata without headers, query secrets, or request bodies."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = time.perf_counter()
        response = None
        try:
            response = self.get_response(request)
            return response
        finally:
            duration_ms = (time.perf_counter() - started) * 1000
            user = getattr(request, "user", None)
            user_id = getattr(user, "pk", None) if getattr(user, "is_authenticated", False) else None
            record_match = _record_id_pattern.search(request.path)
            request_logger.info(
                "request method=%s path=%s status=%s duration_ms=%.2f user_id=%s record_id=%s",
                request.method,
                request.path,
                getattr(response, "status_code", 500),
                duration_ms,
                user_id or "anonymous",
                record_match.group(1) if record_match else "-",
            )
