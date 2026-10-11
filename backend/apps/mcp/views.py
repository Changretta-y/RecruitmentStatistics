"""Django compatibility view for the MCP ASGI service."""

from __future__ import annotations

import json
from typing import Any

from asgiref.sync import async_to_sync
from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import CallToolRequestParams, CallToolResult, TextContent

from .auth import token_verifier
from .server import server
from .tools import audit_evidence_context


def _bearer_challenge(error: str, description: str) -> str:
    return (
        f'Bearer error="{error}", error_description="{description}", '
        f'resource_metadata="{settings.MCP_PROTECTED_RESOURCE_METADATA_URI}"'
    )


def _auth_error(status: int, error: str, description: str) -> JsonResponse:
    response = JsonResponse({"error": error, "error_description": description}, status=status)
    response["WWW-Authenticate"] = _bearer_challenge(error, description)
    return response


def _origin_allowed(request: HttpRequest) -> bool:
    origin = request.headers.get("Origin")
    return not origin or origin in settings.MCP_ALLOWED_ORIGINS


def _required_scope_for_body(body: dict[str, Any]) -> str | None:
    if body.get("method") != "tools/call":
        return None
    params = body.get("params")
    if not isinstance(params, dict):
        return None
    if params.get("name") == "find_applications":
        return "applications:read"
    if params.get("name") in {
        "create_application",
        "upsert_application_stage",
        "preview_application_change",
        "apply_application_change",
    }:
        return "applications:write"
    return None


def _discover_result() -> dict[str, Any]:
    capabilities = server._lowlevel_server.get_capabilities(protocol_version="2026-07-28")
    result: dict[str, Any] = {
        "protocolVersion": "2026-07-28",
        "supportedVersions": ["2026-07-28", "2025-11-25"],
        "capabilities": capabilities.model_dump(mode="json", by_alias=True, exclude_none=True),
        "serverInfo": server._lowlevel_server.server_info_stamp,
        "resultType": "complete",
    }
    if server.instructions:
        result["instructions"] = server.instructions
    return result


async def _list_tools_result() -> dict[str, Any]:
    tools = await server.list_tools()
    return {
        "tools": [tool.model_dump(mode="json", by_alias=True, exclude_none=True) for tool in tools],
        "resultType": "complete",
    }


async def _call_tool_result(params: dict[str, Any]) -> dict[str, Any]:
    try:
        typed = CallToolRequestParams.model_validate(params)
    except Exception:
        return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "Invalid params"}}

    arguments = typed.arguments or {}
    allowed_by_tool = {
        "find_applications": {
            "application_id",
            "company_name",
            "position_name",
            "search",
            "application_status",
            "stage",
            "page",
            "page_size",
        },
        "create_application": {
            "company_name",
            "company_id",
            "position_name",
            "application_time",
            "application_url",
            "notes",
            "application_status",
            "source",
        },
        "upsert_application_stage": {
            "application_id",
            "position_id",
            "stage_type",
            "interview_round",
            "interview_name",
            "scheduled_at",
            "duration_minutes",
        },
        "preview_application_change": {
            "operation",
            "target",
            "change",
            "idempotency_key",
        },
        "apply_application_change": {
            "proposal_id",
            "confirm",
            "idempotency_key",
        },
    }
    allowed = allowed_by_tool.get(typed.name)
    if allowed is not None:
        extra = set(arguments) - allowed
        if extra:
            result = CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text="工具参数包含不支持的字段：" + ", ".join(sorted(extra)) + "。",
                    )
                ],
                is_error=True,
            )
            return result.model_dump(mode="json", by_alias=True, exclude_none=False)

    evidence_token = audit_evidence_context.set(None)
    try:
        result = await server.call_tool(typed.name, arguments)
    except ToolError as exc:
        result = CallToolResult(
            content=[TextContent(type="text", text=str(exc))],
            is_error=True,
            structured_content=audit_evidence_context.get(),
        )
    except Exception:
        # Never expose ORM, SQL, or traceback details through a public MCP
        # response. Expected semantic errors are raised as ToolError above.
        result = CallToolResult(
            content=[TextContent(type="text", text="工具执行失败，数据未写入。")],
            is_error=True,
            structured_content=audit_evidence_context.get(),
        )
    finally:
        audit_evidence_context.reset(evidence_token)
    return result.model_dump(mode="json", by_alias=True, exclude_none=False)


async def _dispatch(body: dict[str, Any]) -> dict[str, Any]:
    request_id = body.get("id")
    method = body.get("method")
    params = body.get("params") or {}
    if not isinstance(method, str) or not isinstance(params, dict):
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32600, "message": "Invalid Request"},
        }

    if method == "server/discover":
        result = _discover_result()
    elif method == "tools/list":
        result = await _list_tools_result()
    elif method == "tools/call":
        result = await _call_tool_result(params)
        if "jsonrpc" in result:
            result["id"] = request_id
            return result
    elif method in {"notifications/initialized", "notifications/cancelled"}:
        return {}
    elif method == "initialize":
        result = {
            "protocolVersion": "2025-11-25",
            "capabilities": server._lowlevel_server.get_capabilities().model_dump(
                mode="json", by_alias=True, exclude_none=True
            ),
            "serverInfo": server._lowlevel_server.server_info_stamp,
        }
    elif method == "ping":
        result = {}
    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": "Method not found"},
        }

    return {"jsonrpc": "2.0", "id": request_id, "result": result}


@method_decorator(csrf_exempt, name="dispatch")
class MCPView(View):
    http_method_names = ["post", "options"]

    def post(self, request: HttpRequest) -> JsonResponse:
        if not _origin_allowed(request):
            return JsonResponse({"error": "invalid_origin"}, status=403)

        authorization = request.headers.get("Authorization", "")
        if not authorization.lower().startswith("bearer "):
            return _auth_error(401, "invalid_token", "Bearer authentication is required.")
        raw_token = authorization[7:].strip()
        access_token = token_verifier.verify_token_sync(raw_token)
        if access_token is None:
            return _auth_error(401, "invalid_token", "The access token is invalid.")
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse(
                {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}},
                status=200,
            )
        if not isinstance(body, dict) or body.get("jsonrpc") != "2.0":
            return JsonResponse(
                {
                    "jsonrpc": "2.0",
                    "id": body.get("id") if isinstance(body, dict) else None,
                    "error": {"code": -32600, "message": "Invalid Request"},
                },
                status=200,
            )

        required_scope = _required_scope_for_body(body)
        if required_scope is not None and required_scope not in access_token.scopes:
            return _auth_error(403, "insufficient_scope", f"Required scope: {required_scope}")

        token = auth_context_var.set(AuthenticatedUser(access_token))
        try:
            result = async_to_sync(_dispatch)(body)
        finally:
            auth_context_var.reset(token)

        if "id" not in body:
            return JsonResponse({}, status=202)
        return JsonResponse(result, status=200)

    def options(self, request: HttpRequest) -> JsonResponse:
        return JsonResponse({}, status=204)
