"""Official MCP Python SDK v2 server definition and ASGI application."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal

from django.conf import settings
from mcp.server.auth.settings import AuthSettings
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from mcp_types import CallToolRequestParams, ToolAnnotations
from pydantic import StrictBool

from .auth import token_verifier
from .tools import (
    ApplicationStatus,
    ApplyChangeResult,
    CreateApplicationResult,
    FindApplicationsResult,
    PreviewChangeResult,
    ProposalChange,
    ProposalTarget,
    Stage,
    UpdatedStageResult,
    create_application_data,
    apply_application_change_data,
    find_applications_data,
    preview_application_change_data,
    upsert_application_stage_data,
    audit_evidence_context,
)


StageWriteType = Literal["assessment", "written_test", "interview"]
InterviewRound = Literal["first", "second", "third", "hr", "other"]


server = MCPServer(
    name="recruitment-progress",
    title="校招进度管理 MCP 服务",
    description="查询并维护当前 OAuth 用户自己的投递进度。",
    version="MCP-003",
    auth=AuthSettings(
        issuer_url=settings.MCP_AUTHORIZATION_ISSUER,
        resource_server_url=settings.MCP_RESOURCE_URI,
        required_scopes=["applications:read", "applications:write"],
        validate_token_resource=True,
    ),
    token_verifier=token_verifier,
)


@server.tool(
    name="find_applications",
    title="查询我的投递进度",
    description=(
        "按公司、岗位、关键词、状态或流程阶段查询当前授权用户自己的 APP-012 投递聚合。"
    ),
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
    structured_output=True,
)
async def find_applications(
    application_id: int | None = None,
    company_name: str | None = None,
    position_name: str | None = None,
    search: str | None = None,
    application_status: ApplicationStatus | None = None,
    stage: Stage | None = None,
    page: int = 1,
    page_size: Literal[10, 20, 50, 100] = 20,
) -> FindApplicationsResult:
    """Return only the authenticated user's company aggregates."""

    return await find_applications_data(
        application_id=application_id,
        company_name=company_name,
        position_name=position_name,
        search=search,
        application_status=application_status,
        stage=stage,
        page=page,
        page_size=page_size,
    )


@server.tool(
    name="create_application",
    title="新增我的投递",
    description=(
        "创建当前授权用户自己的公司投递或追加岗位。会写入投递数据，"
        "复用全局公司目录，但不会写入岗位级招聘 URL。"
    ),
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
    structured_output=True,
)
async def create_application(
    position_name: str,
    company_name: str | None = None,
    company_id: int | None = None,
    application_time: datetime | None = None,
    application_url: str | None = None,
    notes: str | None = None,
    application_status: ApplicationStatus = "applied",
    source: dict[str, Any] | None = None,
) -> CreateApplicationResult:
    """Create or deterministically reuse a user's company/position aggregate."""

    return await create_application_data(
        position_name=position_name,
        company_name=company_name,
        company_id=company_id,
        application_time=application_time,
        application_url=application_url,
        notes=notes,
        application_status=application_status,
        source=source,
    )


@server.tool(
    name="upsert_application_stage",
    title="更新我的投递阶段时间",
    description=(
        "新增或更新当前授权用户自己的测评、笔试或岗位面试时间，"
        "支持清空时间；会写入投递数据并重算只读 current_stage。"
    ),
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
    structured_output=True,
)
async def upsert_application_stage(
    application_id: int,
    stage_type: StageWriteType,
    position_id: int | None = None,
    interview_round: InterviewRound | None = None,
    interview_name: str | None = None,
    scheduled_at: datetime | None = None,
    duration_minutes: int | None = None,
) -> UpdatedStageResult:
    """Upsert one semantic shared stage or position interview."""

    return await upsert_application_stage_data(
        application_id=application_id,
        position_id=position_id,
        stage_type=stage_type,
        interview_round=interview_round,
        interview_name=interview_name,
        scheduled_at=scheduled_at,
        duration_minutes=duration_minutes,
    )


@server.tool(
    name="preview_application_change",
    title="预览投递变更",
    description=(
        "校验当前用户的语义化投递或阶段变更，持久化一份短期提案并返回明确的 before/after 差异。"
        "预览不会修改投递数据；应用前必须由用户明确确认。"
    ),
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
    structured_output=True,
)
async def preview_application_change(
    operation: Literal["upsert_application_stage", "create_application"],
    target: ProposalTarget,
    change: ProposalChange,
    idempotency_key: str | None = None,
) -> PreviewChangeResult:
    """Create a persisted, short-lived semantic change proposal."""

    return await preview_application_change_data(
        operation=operation,
        target=target,
        change=change,
        idempotency_key=idempotency_key,
    )


@server.tool(
    name="apply_application_change",
    title="确认并应用投递变更",
    description=(
        "仅在当前 OAuth 用户、客户端和资源受众匹配，且提案未过期、未消费时应用变更。"
        "confirm 必须是 JSON 布尔值 true；服务会做冲突检查并写入审计。"
    ),
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=True,
        idempotent_hint=True,
        open_world_hint=False,
    ),
    structured_output=True,
)
async def apply_application_change(
    proposal_id: str,
    confirm: StrictBool,
    idempotency_key: str | None = None,
) -> ApplyChangeResult:
    """Consume a proposal exactly once after explicit confirmation."""

    return await apply_application_change_data(
        proposal_id=proposal_id,
        confirm=confirm,
        idempotency_key=idempotency_key,
    )


_TOOL_ARGUMENTS = {
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


async def strict_call_tool(ctx: Any, params: CallToolRequestParams):
    """Reject unknown fields before MCPServer's typed argument conversion."""

    arguments = params.arguments or {}
    allowed = _TOOL_ARGUMENTS.get(params.name)
    if allowed is not None:
        extra = set(arguments) - allowed
        if extra:
            from mcp.server.mcpserver.exceptions import ToolError

            raise ToolError("工具参数包含不支持的字段：" + ", ".join(sorted(extra)) + "。")
    evidence_token = audit_evidence_context.set(None)
    try:
        result = await server._handle_call_tool(ctx, params)  # SDK v2 low-level hook
        evidence = audit_evidence_context.get()
        if evidence and getattr(result, "is_error", False):
            result = result.model_copy(update={"structured_content": evidence})
        return result
    finally:
        audit_evidence_context.reset(evidence_token)


# MCPServer is the public ergonomic API; this low-level replacement only adds
# strict additional-property rejection required by the public tool contract.
server._lowlevel_server.add_request_handler("tools/call", CallToolRequestParams, strict_call_tool)


_transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=list(settings.MCP_ALLOWED_HOSTS),
    allowed_origins=list(settings.MCP_ALLOWED_ORIGINS),
)


mcp_asgi_app = server.streamable_http_app(
    streamable_http_path=settings.MCP_ENDPOINT,
    json_response=True,
    stateless_http=True,
    transport_security=_transport_security,
    host="127.0.0.1",
)


class _ToolScopeMiddleware:
    """Apply per-tool scopes while retaining SDK auth/resource validation.

    The SDK's built-in ``required_scopes`` is intentionally left empty for the
    request route because read and write tools have different requirements.
    The protected-resource metadata route still advertises both scopes.  This
    middleware runs after the SDK authentication middleware and before the
    stateless transport, so a missing tool scope is an HTTP 403 rather than a
    tool-level success response containing an error.
    """

    def __init__(self, app: Any):
        self.app = app

    @staticmethod
    def _required_scope(body: Any) -> str | None:
        if not isinstance(body, dict) or body.get("method") != "tools/call":
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

    @staticmethod
    async def _forbidden(send: Any, required_scope: str) -> None:
        body = json.dumps(
            {
                "error": "insufficient_scope",
                "error_description": f"Required scope: {required_scope}",
            }
        ).encode("utf-8")
        headers = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode("ascii")),
            (
                b"www-authenticate",
                (
                    f'Bearer error="insufficient_scope", '
                    f'error_description="Required scope: {required_scope}", '
                    f'resource_metadata="{settings.MCP_PROTECTED_RESOURCE_METADATA_URI}"'
                ).encode("utf-8"),
            ),
        ]
        await send({"type": "http.response.start", "status": 403, "headers": headers})
        await send({"type": "http.response.body", "body": body})

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        user = scope.get("user")
        if not isinstance(user, AuthenticatedUser) or scope.get("method") != "POST":
            await self.app(scope, receive, send)
            return

        events: list[dict[str, Any]] = []
        chunks: list[bytes] = []
        while True:
            event = await receive()
            events.append(event)
            if event.get("type") == "http.request":
                chunks.append(event.get("body", b""))
                if not event.get("more_body", False):
                    break
            else:
                break
        try:
            body = json.loads(b"".join(chunks))
        except (json.JSONDecodeError, UnicodeDecodeError):
            body = None
        required_scope = self._required_scope(body)
        if required_scope and required_scope not in user.scopes:
            await self._forbidden(send, required_scope)
            return

        async def replay_receive() -> dict[str, Any]:
            if events:
                return events.pop(0)
            return {"type": "http.request", "body": b"", "more_body": False}

        await self.app(scope, replay_receive, send)


# The SDK uses one global required-scope list for its middleware and metadata.
# Keep both scopes in discovery, then make the request route scope-aware per
# tool.  The original RequireAuthMiddleware remains in place with an empty
# global requirement, so invalid/expired/resource-mismatched tokens still use
# the SDK's standard 401 handling.
for _route in mcp_asgi_app.routes:
    if getattr(_route, "path", None) == settings.MCP_ENDPOINT:
        if hasattr(_route.app, "required_scopes"):
            _route.app.required_scopes = []
        _route.app = _ToolScopeMiddleware(_route.app)
        break
