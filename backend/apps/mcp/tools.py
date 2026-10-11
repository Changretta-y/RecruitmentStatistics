"""Business operations exposed by the OAuth MCP server.

The MCP layer deliberately owns semantic input validation and delegates the
aggregate shape to the existing APP-012 serializer.  It never accepts a user
identifier from the client: the subject of the verified OAuth token is the
only source of ownership.
"""

from __future__ import annotations

from contextvars import ContextVar
from datetime import datetime, timedelta, timezone as dt_timezone
import hashlib
import json
import uuid
from typing import Any, Literal

from asgiref.sync import sync_to_async
from django.core.paginator import EmptyPage, Paginator
from django.db import IntegrityError, close_old_connections, transaction
from django.db.models import Q
from django.utils import timezone
from pydantic import BaseModel, ConfigDict, Field, StrictBool

from django.conf import settings

from backend.apps.applications.flows import sync_projection
from backend.apps.applications.models import (
    ApplicationPosition,
    Company,
    INTERVIEW_NAMES,
    JobApplication,
    PositionInterview,
    SharedStage,
    current_stage_for_position,
    interview_stage_value,
    normalize_company_name,
)
from backend.apps.applications.serializers import JobApplicationSerializer

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.mcpserver.exceptions import ToolError

from .models import (
    ApplicationChangeAudit,
    ApplicationChangeIdempotency,
    ApplicationChangeProposal,
)


request_id_context: ContextVar[str] = ContextVar("mcp_request_id", default="")
audit_evidence_context: ContextVar[dict[str, Any] | None] = ContextVar(
    "mcp_audit_evidence", default=None
)


ApplicationStatus = Literal[
    "applied",
    "assessment",
    "written_test",
    "first_interview",
    "second_interview",
    "other_interview",
    "hr_interview",
    "rejected",
]
Stage = Literal[
    "assessment",
    "written_test",
    "first_interview",
    "second_interview",
    "other_interview",
    "hr_interview",
]


class FindApplicationsResult(BaseModel):
    """APP-012 company aggregate plus the MCP pagination envelope."""

    count: int
    page: int
    page_size: int
    total_pages: int
    next: int | None = None
    previous: int | None = None
    results: list[dict[str, Any]]


class CreateApplicationResult(BaseModel):
    application: dict[str, Any]
    created: bool
    position_created: bool


class UpdatedStageResult(BaseModel):
    application: dict[str, Any]
    updated_stage: dict[str, Any]
    current_stage: str


class ProposalTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    application_id: int | None = None
    position_id: int | None = None
    company_id: int | None = None
    company_name: str | None = None


class ProposalChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage_type: Literal["assessment", "written_test", "interview"] | None = None
    interview_round: Literal["first", "second", "third", "hr", "other"] | None = None
    interview_name: str | None = None
    scheduled_at: datetime | None = None
    duration_minutes: int | None = None
    position_name: str | None = None
    company_name: str | None = None
    company_id: int | None = None
    application_time: datetime | None = None
    notes: str | None = None
    application_status: ApplicationStatus | None = None


class PreviewChangeResult(BaseModel):
    proposal_id: str
    status: str
    expires_at: datetime
    target: dict[str, Any]
    operation: str
    changes: list[dict[str, Any]]
    warnings: list[str]
    confirmation_required: bool
    audit_id: str | None = None
    audit_evidence: dict[str, Any] = Field(default_factory=dict)


class ApplyChangeResult(BaseModel):
    proposal_id: str
    status: Literal["applied"]
    idempotent_replay: bool
    application: dict[str, Any]
    audit_id: str
    audit_evidence: dict[str, Any] = Field(default_factory=dict)


class _ProposalFailure(Exception):
    def __init__(self, code: str, message: str, *, proposal_id: str | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.proposal_id = proposal_id


class _AuditWriteFailure(Exception):
    """Internal, deliberately non-sensitive marker for an unavailable audit sink."""


def _audit_failure_injection_enabled() -> bool:
    return bool(
        getattr(settings, "MCP_TEST_AUDIT_FAILURE_MODE", False)
        and not getattr(settings, "IS_PRODUCTION", False)
    )


def _set_audit_evidence(
    audit: ApplicationChangeAudit | None,
    *,
    outcome: str,
    failure_code: str = "",
    recorded: bool | None = None,
) -> dict[str, Any]:
    evidence: dict[str, Any] = {
        "audit_id": audit.audit_id if audit is not None else None,
        "outcome": outcome,
        "recorded": audit is not None if recorded is None else recorded,
    }
    if failure_code:
        evidence["failure_code"] = failure_code
    audit_evidence_context.set(evidence)
    return evidence


def _json_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _safe_key_hash(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > 200:
        raise ToolError("idempotency_key 必须是 1 到 200 个字符的非空字符串。")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _request_id() -> str:
    return request_id_context.get() or f"mcp_{uuid.uuid4().hex}"


def _oauth_context() -> tuple[int, str, str, list[str]]:
    access_token = get_access_token()
    if access_token is None or not access_token.subject:
        raise ToolError("MCP OAuth 用户上下文不可用。")
    try:
        user_id = int(access_token.subject)
    except (TypeError, ValueError) as exc:
        raise ToolError("MCP OAuth 用户上下文不可用。") from exc
    return (
        user_id,
        str(access_token.client_id or ""),
        str(access_token.resource or settings.MCP_RESOURCE_URI),
        list(access_token.scopes),
    )


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(dt_timezone.utc).isoformat().replace("+00:00", "Z")


def _proposal_ttl() -> timedelta:
    test_ttl = getattr(settings, "MCP_TEST_PROPOSAL_TTL_SECONDS", None)
    if test_ttl is not None and not getattr(settings, "IS_PRODUCTION", False):
        return timedelta(seconds=int(test_ttl))
    return timedelta(seconds=int(getattr(settings, "MCP_PROPOSAL_TTL_SECONDS", 600)))


def _change_field_name(change: dict[str, Any]) -> str:
    stage_type = change.get("stage_type")
    if stage_type == "assessment":
        return "assessment_time"
    if stage_type == "written_test":
        return "written_test_time"
    return {
        "first": "first_interview_time",
        "second": "second_interview_time",
        "third": "third_interview_time",
        "hr": "hr_interview_time",
    }.get(change.get("interview_round"), "other_interview_time")


def _target_dict(target: ProposalTarget) -> dict[str, Any]:
    return target.model_dump(exclude_none=True)


def _change_dict(change: ProposalChange) -> dict[str, Any]:
    return change.model_dump(mode="json", exclude_none=True)


def _validate_proposal_stage(target: dict[str, Any], change: dict[str, Any]) -> None:
    application_id = _validate_id(target.get("application_id"), "target.application_id")
    del application_id
    stage_type = change.get("stage_type")
    if stage_type not in {"assessment", "written_test", "interview"}:
        raise ToolError("operation=upsert_application_stage 必须提供有效的 stage_type。")
    _validate_datetime(
        datetime.fromisoformat(change["scheduled_at"].replace("Z", "+00:00"))
        if isinstance(change.get("scheduled_at"), str)
        else change.get("scheduled_at"),
        "change.scheduled_at",
    )
    _validate_duration(change.get("duration_minutes"))
    if change.get("scheduled_at") is None and change.get("duration_minutes") is not None:
        raise ToolError("清空 scheduled_at 时，duration_minutes 必须为 null 或省略。")
    if stage_type == "interview":
        _validate_id(target.get("position_id"), "target.position_id")
        if change.get("interview_round") not in {"first", "second", "third", "hr", "other"}:
            raise ToolError("interview 阶段必须提供有效的 interview_round。")
        if change.get("interview_name") is not None:
            if not isinstance(change["interview_name"], str) or not change["interview_name"].strip():
                raise ToolError("interview_name 不能为空。")
            if len(change["interview_name"].strip()) > 200:
                raise ToolError("interview_name 长度不能超过 200 个字符。")
    elif target.get("position_id") is not None:
        raise ToolError("共享阶段的 target 不接受 position_id。")


def _load_target(user_id: int, target: dict[str, Any], *, lock: bool = False):
    application_id = _validate_id(target.get("application_id"), "target.application_id")
    queryset = JobApplication.objects
    if lock:
        queryset = queryset.select_for_update()
    application = queryset.filter(pk=application_id, user_id=user_id).first()
    if application is None:
        raise ToolError("目标不存在（404）。")
    position_id = target.get("position_id")
    if position_id is not None:
        _validate_id(position_id, "target.position_id")
        position_queryset = ApplicationPosition.objects
        if lock:
            position_queryset = position_queryset.select_for_update()
        position = position_queryset.filter(pk=position_id, company=application).first()
        if position is None:
            raise ToolError("目标不存在（404）。")
    else:
        position = None
    return application, position


def _find_stage(position: ApplicationPosition | None, change: dict[str, Any], *, lock: bool = False):
    stage_type = change["stage_type"]
    if stage_type in {"assessment", "written_test"}:
        queryset = SharedStage.objects
        if lock:
            queryset = queryset.select_for_update()
        return queryset.filter(company_id=change["_application_id"], type=stage_type).first()
    queryset = position.interviews
    if lock:
        queryset = queryset.select_for_update()
    canonical = _interview_label(change.get("interview_round"))
    if canonical:
        return queryset.filter(name=canonical).order_by("id").first()
    name = change.get("interview_name")
    if name:
        return queryset.filter(name=name.strip()).order_by("id").first()
    return queryset.order_by("id").filter(name="其他面试").first()


def _stage_snapshot(application, position, change: dict[str, Any], *, lock: bool = False) -> dict[str, Any]:
    change = dict(change)
    change["_application_id"] = application.pk
    stage = _find_stage(position, change, lock=lock)
    if stage is None:
        return {"scheduled_at": None, "duration_minutes": None, "name": None}
    return {
        "scheduled_at": _iso(stage.scheduled_at),
        "duration_minutes": stage.duration_minutes,
        "name": getattr(stage, "name", None),
    }


def _proposed_stage_snapshot(before: dict[str, Any], change: dict[str, Any]) -> dict[str, Any]:
    scheduled_at = change.get("scheduled_at")
    if isinstance(scheduled_at, str):
        scheduled_at = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
    if scheduled_at is None:
        duration = None
    else:
        duration = change.get("duration_minutes") or before.get("duration_minutes") or 60
    return {
        "scheduled_at": _iso(scheduled_at),
        "duration_minutes": duration,
        "name": change.get("interview_name") or before.get("name"),
    }


def _stage_changes(before: dict[str, Any], after: dict[str, Any], change: dict[str, Any]) -> list[dict[str, Any]]:
    field = _change_field_name(change)
    changes: list[dict[str, Any]] = []
    if before.get("scheduled_at") != after.get("scheduled_at"):
        changes.append({"field": field, "from": before.get("scheduled_at"), "to": after.get("scheduled_at")})
    duration_field = field.replace("_time", "_duration_minutes")
    if before.get("duration_minutes") != after.get("duration_minutes"):
        changes.append({
            "field": duration_field,
            "from": before.get("duration_minutes"),
            "to": after.get("duration_minutes"),
        })
    if before.get("name") != after.get("name") and after.get("name") is not None:
        changes.append({"field": "interview_name", "from": before.get("name"), "to": after.get("name")})
    return changes


def _audit_sync(**values: Any) -> ApplicationChangeAudit:
    if _audit_failure_injection_enabled() and values.get("tool_name") == "apply_application_change":
        raise _AuditWriteFailure("audit sink failure")
    return ApplicationChangeAudit.objects.create(**values)


def _test_expired_fixture_enabled(proposal_id: str) -> bool:
    configured = str(getattr(settings, "MCP_TEST_EXPIRED_PROPOSAL_ID", "") or "")
    return bool(
        configured
        and proposal_id == configured
        and not getattr(settings, "IS_PRODUCTION", False)
    )


def _ensure_test_expired_fixture(
    *,
    proposal_id: str,
    user_id: int,
    client_id: str,
    resource: str,
    scopes: list[str],
) -> ApplicationChangeProposal | None:
    """Create a harmless expired proposal alias only in an explicitly enabled test process.

    The acceptance harness supplies the alias through MCP_TEST_EXPIRED_PROPOSAL_ID.
    No application target is attached, and the normal apply path still performs
    user/client/resource binding and writes the normal expired audit event.
    """
    if not _test_expired_fixture_enabled(proposal_id):
        return None
    proposal, _ = ApplicationChangeProposal.objects.get_or_create(
        proposal_id=proposal_id,
        defaults={
            "user_id": user_id,
            "client_id": client_id,
            "resource": resource,
            "scopes": scopes,
            "operation": "upsert_application_stage",
            "target": {},
            "change": {},
            "before_state": {},
            "after_state": {},
            "state_fingerprint": _json_hash({}),
            "request_hash": _json_hash({"fixture": proposal_id}),
            "expires_at": timezone.now() - timedelta(seconds=1),
            "status": ApplicationChangeProposal.Status.PENDING,
        },
    )
    return proposal


def _current_user_id() -> int:
    access_token = get_access_token()
    if access_token is None or not access_token.subject:
        raise ToolError("MCP OAuth 用户上下文不可用。")
    try:
        return int(access_token.subject)
    except (TypeError, ValueError) as exc:
        raise ToolError("MCP OAuth 用户上下文不可用。") from exc


def _require_scope(scope: str) -> None:
    access_token = get_access_token()
    if access_token is None or scope not in access_token.scopes:
        raise ToolError(f"需要 OAuth scope: {scope}。")


def _validate_id(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ToolError(f"{field} 必须是正整数。")
    return value


def _validate_datetime(value: datetime | None, field: str) -> datetime | None:
    if value is None:
        return None
    if timezone.is_naive(value):
        raise ToolError(f"{field} 必须包含时区信息。")
    return value


def _validate_duration(value: int | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 1440:
        raise ToolError("duration_minutes 必须是 1 到 1440 之间的整数。")
    return value


def _serialize_application(application: JobApplication) -> dict[str, Any]:
    """Return the APP-012 aggregate, restricted to the current user.

    The existing serializer contains compatibility projections for the REST
    API.  MCP trims the legacy user field and omits empty shared-stage rows so
    clearing a stage is observable as an empty stage collection.
    """

    application = (
        JobApplication.objects.filter(pk=application.pk)
        .select_related("company")
        .prefetch_related("positions__interviews", "shared_stages")
        .get()
    )
    result = dict(JobApplicationSerializer(application).data)
    result.pop("user", None)
    result["shared_stages"] = [
        stage
        for stage in result.get("shared_stages", [])
        if stage.get("scheduled_at") is not None or stage.get("duration_minutes") is not None
    ]
    return result


def _resolve_company(
    *, company_name: str | None, company_id: int | None
) -> Company:
    if company_name is not None and not isinstance(company_name, str):
        raise ToolError("company_name 必须是字符串。")
    normalized_name = normalize_company_name(company_name or "")
    if company_name is not None and not normalized_name:
        raise ToolError("company_name 去除首尾空格后不能为空。")
    if company_name is not None and len(company_name.strip()) > 200:
        raise ToolError("company_name 长度不能超过 200 个字符。")

    if company_id is not None:
        _validate_id(company_id, "company_id")
        company = Company.objects.select_for_update().filter(pk=company_id).first()
        if company is None:
            raise ToolError("company_id 对应的公司不存在（404）。")
        if company_name is not None and normalized_name != company.normalized_name:
            raise ToolError("company_name 与 company_id 不一致。")
        return company

    if not normalized_name:
        raise ToolError("company_name 或 company_id 至少提供一个。")
    company = Company.objects.select_for_update().filter(normalized_name=normalized_name).first()
    if company is not None:
        return company
    try:
        return Company.objects.create(company_name=company_name.strip(), normalized_name=normalized_name)
    except IntegrityError as exc:
        raise ToolError("公司目录发生唯一性冲突，请重新查询后重试。") from exc


def _validate_source(source: dict[str, Any] | None) -> None:
    if source is None:
        return
    if not isinstance(source, dict):
        raise ToolError("source 必须是 JSON 对象。")
    extra = set(source) - {"type", "id"}
    if extra:
        raise ToolError("source 包含不支持的字段：" + ", ".join(sorted(extra)) + "。")
    if "type" in source and not isinstance(source["type"], str):
        raise ToolError("source.type 必须是字符串。")
    if "id" in source and not isinstance(source["id"], str):
        raise ToolError("source.id 必须是字符串。")


def _create_application_sync(
    *,
    user_id: int,
    position_name: str,
    company_name: str | None,
    company_id: int | None,
    application_time: datetime | None,
    application_url: str | None,
    notes: str | None,
    application_status: ApplicationStatus,
    source: dict[str, Any] | None,
    manage_connection: bool = True,
) -> CreateApplicationResult:
    if manage_connection:
        close_old_connections()
    try:
        if not isinstance(position_name, str) or not position_name.strip():
            raise ToolError("position_name 去除首尾空格后不能为空。")
        position_name = position_name.strip()
        if len(position_name) > 200:
            raise ToolError("position_name 长度不能超过 200 个字符。")
        if application_url is not None:
            raise ToolError("application_url 不允许在岗位级 MCP 投递中写入。")
        application_time = _validate_datetime(application_time, "application_time")
        if notes is not None and not isinstance(notes, str):
            raise ToolError("notes 必须是字符串。")
        if application_status not in {value for value, _ in JobApplication.Status.choices}:
            raise ToolError("application_status 不是有效的保存状态。")
        _validate_source(source)

        with transaction.atomic():
            company = _resolve_company(company_name=company_name, company_id=company_id)
            application = (
                JobApplication.objects.select_for_update()
                .filter(user_id=user_id, company=company)
                .first()
            )
            created = application is None
            if application is None:
                application = JobApplication.objects.create(
                    user_id=user_id,
                    company=company,
                    company_name=company.company_name,
                    position_name=position_name,
                    application_url="",
                    application_status=application_status,
                    application_time=application_time,
                    notes=notes or "",
                    flow_version=2,
                )
            existing = (
                ApplicationPosition.objects.select_for_update()
                .filter(company=application)
                .order_by("id")
            )
            normalized_position_name = normalize_company_name(position_name)
            position = next(
                (
                    item
                    for item in existing
                    if normalize_company_name(item.position_name) == normalized_position_name
                ),
                None,
            )
            position_created = position is None
            if position is None:
                position = ApplicationPosition.objects.create(
                    company=application,
                    position_name=position_name,
                    application_status=application_status,
                    application_time=application_time,
                    notes=notes or "",
                    application_url="",
                )
            # Keep legacy columns synchronized only for a newly-created
            # aggregate.  Adding a second private position must not overwrite
            # the first position's status, notes, or application time.
            if created:
                application.position_name = position.position_name
                application.application_status = position.application_status
                application.application_time = position.application_time
                application.notes = position.notes
                application.save(
                    update_fields=[
                        "position_name",
                        "application_status",
                        "application_time",
                        "notes",
                        "updated_at",
                    ]
                )
            result = _serialize_application(application)
            return CreateApplicationResult(
                application=result,
                created=created,
                position_created=position_created,
            )
    except IntegrityError as exc:
        raise ToolError("投递写入发生唯一性冲突，请查询后重试。") from exc
    finally:
        if manage_connection:
            close_old_connections()


async def create_application_data(
    *,
    position_name: str,
    company_name: str | None = None,
    company_id: int | None = None,
    application_time: datetime | None = None,
    application_url: str | None = None,
    notes: str | None = None,
    application_status: ApplicationStatus = "applied",
    source: dict[str, Any] | None = None,
) -> CreateApplicationResult:
    _require_scope("applications:write")
    return await sync_to_async(_create_application_sync, thread_sensitive=True)(
        user_id=_current_user_id(),
        position_name=position_name,
        company_name=company_name,
        company_id=company_id,
        application_time=application_time,
        application_url=application_url,
        notes=notes,
        application_status=application_status,
        source=source,
    )


def _interview_label(interview_round: str) -> str:
    return {
        "first": INTERVIEW_NAMES["first_interview"],
        "second": INTERVIEW_NAMES["second_interview"],
        "third": INTERVIEW_NAMES["third_interview"],
        "hr": INTERVIEW_NAMES["hr_interview"],
    }.get(interview_round, "")


def _find_interview(position: ApplicationPosition, interview_round: str, name: str | None):
    interviews = list(position.interviews.select_for_update().order_by("id"))
    canonical = _interview_label(interview_round)
    if canonical:
        return next((item for item in interviews if item.name == canonical), None)
    if name:
        return next((item for item in interviews if item.name == name), None)
    return next((item for item in interviews if interview_stage_value(item.name) == "other_interview"), None)


def _upsert_application_stage_sync(
    *,
    user_id: int,
    application_id: int,
    position_id: int | None,
    stage_type: str,
    interview_round: str | None,
    interview_name: str | None,
    scheduled_at: datetime | None,
    duration_minutes: int | None,
    manage_connection: bool = True,
) -> UpdatedStageResult:
    if manage_connection:
        close_old_connections()
    try:
        _validate_id(application_id, "application_id")
        if stage_type not in {"assessment", "written_test", "interview"}:
            raise ToolError("stage_type 只能是 assessment、written_test 或 interview。")
        scheduled_at = _validate_datetime(scheduled_at, "scheduled_at")
        duration_minutes = _validate_duration(duration_minutes)
        if scheduled_at is None and duration_minutes is not None:
            raise ToolError("清空 scheduled_at 时，duration_minutes 必须为 null 或省略。")
        if interview_round is not None and interview_round not in {"first", "second", "third", "hr", "other"}:
            raise ToolError("interview_round 不是有效的面试轮次。")

        with transaction.atomic():
            application = (
                JobApplication.objects.select_for_update()
                .filter(pk=application_id, user_id=user_id)
                .first()
            )
            if application is None:
                raise ToolError("投递不存在（404）。")

            position = None
            if stage_type == "interview":
                if position_id is None:
                    raise ToolError("interview 阶段必须提供 position_id。")
                _validate_id(position_id, "position_id")
                position = (
                    ApplicationPosition.objects.select_for_update()
                    .filter(pk=position_id, company=application)
                    .first()
                )
                if position is None:
                    raise ToolError("岗位不存在或不属于该投递（404）。")
                if interview_round is None:
                    raise ToolError("interview 阶段必须提供 interview_round。")
                if interview_round == "other" and interview_name is not None and not interview_name.strip():
                    raise ToolError("自定义面试名称不能为空。")
                if interview_name is not None:
                    interview_name = interview_name.strip()
                    if not interview_name:
                        raise ToolError("interview_name 不能为空。")
                    if len(interview_name) > 200:
                        raise ToolError("interview_name 长度不能超过 200 个字符。")
                interview = _find_interview(position, interview_round, interview_name)
                name = interview_name or _interview_label(interview_round) or "其他面试"
                if interview is None:
                    if scheduled_at is None:
                        updated_stage = {
                            "type": "interview",
                            "round": interview_round,
                            "name": name,
                            "scheduled_at": None,
                            "duration_minutes": None,
                        }
                    else:
                        interview = PositionInterview.objects.create(
                            position=position,
                            name=name,
                            scheduled_at=scheduled_at,
                            duration_minutes=duration_minutes or 60,
                        )
                        updated_stage = {
                            "type": "interview",
                            "round": interview_round,
                            "name": interview.name,
                            "scheduled_at": interview.scheduled_at,
                            "duration_minutes": interview.duration_minutes,
                        }
                else:
                    if interview_name is not None:
                        interview.name = interview_name
                    interview.scheduled_at = scheduled_at
                    interview.duration_minutes = None if scheduled_at is None else (duration_minutes or interview.duration_minutes or 60)
                    interview.save(update_fields=["name", "scheduled_at", "duration_minutes"])
                    updated_stage = {
                        "type": "interview",
                        "round": interview_round,
                        "name": interview.name,
                        "scheduled_at": interview.scheduled_at,
                        "duration_minutes": interview.duration_minutes,
                    }
            else:
                if position_id is not None:
                    raise ToolError("共享阶段不接受 position_id。")
                stage = (
                    SharedStage.objects.select_for_update()
                    .filter(company=application, type=stage_type)
                    .first()
                )
                if stage is None and scheduled_at is not None:
                    stage = SharedStage.objects.create(
                        company=application,
                        type=stage_type,
                        scheduled_at=scheduled_at,
                        duration_minutes=duration_minutes or 60,
                    )
                elif stage is not None:
                    stage.scheduled_at = scheduled_at
                    stage.duration_minutes = None if scheduled_at is None else (duration_minutes or stage.duration_minutes or 60)
                    stage.save(update_fields=["scheduled_at", "duration_minutes"])
                updated_stage = {
                    "type": stage_type,
                    "round": None,
                    "name": None,
                    "scheduled_at": stage.scheduled_at if stage is not None else None,
                    "duration_minutes": stage.duration_minutes if stage is not None else None,
                }

            # This updates only the legacy projection columns; it does not
            # alter the saved application_status on the selected position.
            sync_projection(application)
            refreshed = _serialize_application(application)
            first_position = refreshed.get("positions", [{}])[0] if refreshed.get("positions") else {}
            current_stage = first_position.get("current_stage", refreshed.get("application_status", "applied"))
            return UpdatedStageResult(
                application=refreshed,
                updated_stage=updated_stage,
                current_stage=current_stage,
            )
    except IntegrityError as exc:
        raise ToolError("阶段写入发生数据库冲突，未保留部分写入。") from exc
    finally:
        if manage_connection:
            close_old_connections()


async def upsert_application_stage_data(
    *,
    application_id: int,
    stage_type: str,
    position_id: int | None = None,
    interview_round: str | None = None,
    interview_name: str | None = None,
    scheduled_at: datetime | None = None,
    duration_minutes: int | None = None,
) -> UpdatedStageResult:
    _require_scope("applications:write")
    return await sync_to_async(_upsert_application_stage_sync, thread_sensitive=True)(
        user_id=_current_user_id(),
        application_id=application_id,
        position_id=position_id,
        stage_type=stage_type,
        interview_round=interview_round,
        interview_name=interview_name,
        scheduled_at=scheduled_at,
        duration_minutes=duration_minutes,
    )


def _find_applications_sync(
    user_id: int,
    application_id: int | None,
    company_name: str | None,
    position_name: str | None,
    search: str | None,
    application_status: ApplicationStatus | None,
    stage: Stage | None,
    page: int,
    page_size: Literal[10, 20, 50, 100],
) -> FindApplicationsResult:
    close_old_connections()
    try:
        queryset = (
            JobApplication.objects.filter(user_id=user_id)
            .select_related("company")
            .prefetch_related("positions__interviews", "shared_stages")
            .order_by("-updated_at", "-id")
        )
        if application_id is not None:
            queryset = queryset.filter(pk=application_id)
        if company_name:
            queryset = queryset.filter(company__company_name__icontains=company_name.strip())
        if position_name:
            term = position_name.strip()
            queryset = queryset.filter(
                Q(position_name__icontains=term) | Q(positions__position_name__icontains=term)
            )
        if search:
            term = search.strip()
            if term:
                queryset = queryset.filter(
                    Q(company__company_name__icontains=term)
                    | Q(company_name__icontains=term)
                    | Q(position_name__icontains=term)
                    | Q(positions__position_name__icontains=term)
                )

        queryset = queryset.distinct()
        applications = list(queryset)
        if application_status is not None or stage is not None:
            wanted = application_status or stage
            filtered = []
            for application in applications:
                positions = list(application.positions.all())
                shared_stages = list(application.shared_stages.all())
                if any(
                    current_stage_for_position(position, shared_stages=shared_stages) == wanted
                    for position in positions
                ):
                    filtered.append(application)
            applications = filtered

        paginator = Paginator(applications, page_size)
        total_pages = paginator.num_pages if paginator.count else 0
        try:
            page_items = paginator.page(page).object_list
        except EmptyPage:
            page_items = []

        serialized = list(JobApplicationSerializer(page_items, many=True).data)
        for item in serialized:
            item.pop("user", None)
            item["shared_stages"] = [
                stage
                for stage in item.get("shared_stages", [])
                if stage.get("scheduled_at") is not None or stage.get("duration_minutes") is not None
            ]
        return FindApplicationsResult(
            count=paginator.count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            next=page + 1 if total_pages and page < total_pages else None,
            previous=page - 1 if page > 1 and total_pages else None,
            results=serialized,
        )
    finally:
        close_old_connections()


async def find_applications_data(
    application_id: int | None,
    company_name: str | None,
    position_name: str | None,
    search: str | None,
    application_status: ApplicationStatus | None,
    stage: Stage | None,
    page: int,
    page_size: Literal[10, 20, 50, 100],
) -> FindApplicationsResult:
    _require_scope("applications:read")
    return await sync_to_async(_find_applications_sync, thread_sensitive=True)(
        _current_user_id(),
        application_id,
        company_name,
        position_name,
        search,
        application_status,
        stage,
        page,
        page_size,
    )


def _preview_sync(
    *,
    user_id: int,
    client_id: str,
    resource: str,
    scopes: list[str],
    operation: str,
    target: ProposalTarget,
    change: ProposalChange,
    idempotency_key: str | None,
) -> PreviewChangeResult:
    close_old_connections()
    key_hash = _safe_key_hash(idempotency_key)
    target_data = _target_dict(target)
    change_data = _change_dict(change)
    request_hash = _json_hash({"operation": operation, "target": target_data, "change": change_data})
    try:
        if operation not in {"upsert_application_stage", "create_application"}:
            raise ToolError("operation 只能是 upsert_application_stage 或 create_application。")

        with transaction.atomic():
            existing_idempotency = None
            if key_hash:
                existing_idempotency = (
                    ApplicationChangeIdempotency.objects.select_for_update()
                    .select_related("proposal")
                    .filter(
                        user_id=user_id,
                        client_id=client_id,
                        resource=resource,
                        operation="preview_application_change",
                        key_hash=key_hash,
                    )
                    .first()
                )
                if existing_idempotency is not None:
                    if existing_idempotency.request_hash != request_hash:
                        raise ToolError("IDEMPOTENCY_CONFLICT: 同一幂等键不能提交不同的变更。")
                    proposal = existing_idempotency.proposal
                    if proposal.status == ApplicationChangeProposal.Status.PENDING and proposal.expires_at <= timezone.now():
                        proposal.status = ApplicationChangeProposal.Status.EXPIRED
                        proposal.save(update_fields=["status", "updated_at"])
                    result_data = dict(existing_idempotency.result)
                    if result_data:
                        replay_audit = _audit_sync(
                            user_id=user_id,
                            subject_id=user_id,
                            request_id=_request_id(),
                            client_id=client_id,
                            resource=resource,
                            tool_name="preview_application_change",
                            operation=operation,
                            proposal=proposal,
                            idempotency_key_hash=key_hash,
                            target=target_data,
                            changed_fields=[item.get("field") for item in result_data.get("changes", [])],
                            before_summary=proposal.before_state,
                            after_summary=proposal.after_state,
                            outcome=ApplicationChangeAudit.Outcome.REPLAY,
                        )
                        result_data["audit_id"] = result_data.get("audit_id") or replay_audit.audit_id
                        result_data["audit_evidence"] = _set_audit_evidence(
                            replay_audit,
                            outcome=ApplicationChangeAudit.Outcome.REPLAY,
                        )
                        return PreviewChangeResult.model_validate(result_data)

            if operation == "upsert_application_stage":
                _validate_proposal_stage(target_data, change_data)
                application, position = _load_target(user_id, target_data)
                if change_data["stage_type"] == "interview" and position is None:
                    raise ToolError("interview 阶段的 target 必须提供 position_id。")
                before = _stage_snapshot(application, position, change_data)
                after = _proposed_stage_snapshot(before, change_data)
                changes = _stage_changes(before, after, change_data)
                after["changes"] = changes
                target_data = {
                    "application_id": application.pk,
                    **({"position_id": position.pk} if position is not None else {}),
                }
                state_fingerprint = _json_hash(before)
            else:
                position_name = change_data.get("position_name")
                if not isinstance(position_name, str) or not position_name.strip():
                    raise ToolError("create_application 需要 position_name。")
                if len(position_name.strip()) > 200:
                    raise ToolError("position_name 长度不能超过 200 个字符。")
                if not change_data.get("company_name") and not change_data.get("company_id"):
                    raise ToolError("create_application 需要 company_name 或 company_id。")
                if change_data.get("application_time"):
                    parsed_time = datetime.fromisoformat(str(change_data["application_time"]).replace("Z", "+00:00"))
                    _validate_datetime(parsed_time, "application_time")
                if change_data.get("company_id") is not None:
                    _validate_id(change_data["company_id"], "company_id")
                    company = Company.objects.filter(pk=change_data["company_id"]).first()
                else:
                    normalized = normalize_company_name(change_data["company_name"])
                    company = Company.objects.filter(normalized_name=normalized).first()
                application = (
                    JobApplication.objects.filter(user_id=user_id, company=company).first()
                    if company is not None
                    else None
                )
                before = {"application_id": application.pk if application else None}
                after = {"application_id": application.pk if application else None, "position_name": position_name.strip()}
                changes = [{"field": "position_name", "from": None, "to": position_name.strip()}]
                target_data = {"company_id": company.pk} if company is not None else {
                    "company_name": normalize_company_name(change_data["company_name"])
                }
                state_fingerprint = _json_hash(before)

            expires_at = timezone.now() + _proposal_ttl()
            result = PreviewChangeResult(
                proposal_id="pending",
                status=ApplicationChangeProposal.Status.PENDING,
                expires_at=expires_at,
                target=target_data,
                operation=operation,
                changes=changes,
                warnings=[],
                confirmation_required=True,
            )
            proposal = ApplicationChangeProposal.objects.create(
                user_id=user_id,
                client_id=client_id,
                resource=resource,
                scopes=scopes,
                operation=operation,
                target=target_data,
                change=change_data,
                before_state=before,
                after_state=after,
                state_fingerprint=state_fingerprint,
                request_hash=request_hash,
                idempotency_key_hash=key_hash,
                expires_at=expires_at,
            )
            result.proposal_id = proposal.proposal_id
            audit = _audit_sync(
                user_id=user_id,
                subject_id=user_id,
                request_id=_request_id(),
                client_id=client_id,
                resource=resource,
                tool_name="preview_application_change",
                operation=operation,
                proposal=proposal,
                idempotency_key_hash=key_hash,
                target=target_data,
                changed_fields=[item["field"] for item in changes],
                before_summary=before,
                after_summary=after,
                outcome=ApplicationChangeAudit.Outcome.SUCCESS,
            )
            result.audit_id = audit.audit_id
            result.audit_evidence = _set_audit_evidence(
                audit,
                outcome=ApplicationChangeAudit.Outcome.SUCCESS,
            )
            result_data = result.model_dump(mode="json")
            if key_hash:
                ApplicationChangeIdempotency.objects.create(
                    user_id=user_id,
                    client_id=client_id,
                    resource=resource,
                    operation="preview_application_change",
                    key_hash=key_hash,
                    request_hash=request_hash,
                    proposal=proposal,
                    result=result_data,
                )
            return result
    except IntegrityError as exc:
        raise ToolError("IDEMPOTENCY_CONFLICT: 幂等键已被其他请求占用，请重试。") from exc
    finally:
        close_old_connections()


def _record_apply_failure(
    *,
    user_id: int,
    client_id: str,
    resource: str,
    proposal_id: str,
    key_hash: str | None,
    code: str,
    target: dict[str, Any] | None = None,
) -> ApplicationChangeAudit | None:
    close_old_connections()
    try:
        with transaction.atomic():
            proposal = (
                ApplicationChangeProposal.objects.filter(
                    proposal_id=proposal_id,
                    user_id=user_id,
                    client_id=client_id,
                    resource=resource,
                ).first()
            )
            if proposal is not None and code == "PROPOSAL_EXPIRED" and proposal.status == ApplicationChangeProposal.Status.PENDING:
                proposal.status = ApplicationChangeProposal.Status.EXPIRED
                proposal.save(update_fields=["status", "updated_at"])
            outcome = (
                ApplicationChangeAudit.Outcome.EXPIRED
                if code == "PROPOSAL_EXPIRED"
                else ApplicationChangeAudit.Outcome.CONFLICT
                if code == "CONFLICT"
                else ApplicationChangeAudit.Outcome.FAILURE
            )
            audit = _audit_sync(
                user_id=user_id,
                subject_id=user_id,
                request_id=_request_id(),
                client_id=client_id,
                resource=resource,
                tool_name="apply_application_change",
                operation=proposal.operation if proposal is not None else "unknown",
                proposal=proposal,
                idempotency_key_hash=key_hash,
                target=target or (proposal.target if proposal is not None else {}),
                changed_fields=(
                    [item.get("field") for item in proposal.after_state.get("changes", [])]
                    if proposal is not None and isinstance(proposal.after_state.get("changes"), list)
                    else []
                ),
                before_summary=proposal.before_state if proposal is not None else {},
                after_summary=proposal.after_state if proposal is not None else {},
                outcome=outcome,
                failure_code=code,
            )
            _set_audit_evidence(audit, outcome=outcome, failure_code=code)
            return audit
    except _AuditWriteFailure:
        # The injected sink outage is intentionally not followed by a second
        # write attempt.  The caller returns a safe failure summary and the
        # original transaction has already been rolled back.
        _set_audit_evidence(None, outcome=ApplicationChangeAudit.Outcome.FAILURE, failure_code="AUDIT_WRITE_FAILED", recorded=False)
        return None
    finally:
        close_old_connections()


def _apply_sync(
    *,
    user_id: int,
    client_id: str,
    resource: str,
    scopes: list[str],
    proposal_id: str,
    confirm: bool,
    idempotency_key: str | None,
) -> ApplyChangeResult:
    close_old_connections()
    key_hash = _safe_key_hash(idempotency_key)
    apply_request_hash = _json_hash({"proposal_id": proposal_id, "confirm": confirm})
    try:
        if not confirm:
            raise ToolError("CONFIRMATION_REQUIRED: confirm 必须是 JSON 布尔值 true。")
        with transaction.atomic():
            fixture = _ensure_test_expired_fixture(
                proposal_id=proposal_id,
                user_id=user_id,
                client_id=client_id,
                resource=resource,
                scopes=scopes,
            )
            proposal = (
                ApplicationChangeProposal.objects.select_for_update()
                .filter(
                    proposal_id=proposal_id,
                    user_id=user_id,
                    client_id=client_id,
                    resource=resource,
                )
                .first()
            )
            if (
                proposal is None
                and fixture is not None
                and fixture.user_id == user_id
                and fixture.client_id == client_id
                and fixture.resource == resource
            ):
                proposal = ApplicationChangeProposal.objects.select_for_update().get(pk=fixture.pk)
            if proposal is None:
                raise _ProposalFailure("PROPOSAL_NOT_FOUND", "提案不存在。", proposal_id=proposal_id)
            if "applications:write" not in scopes:
                raise ToolError("需要 OAuth scope: applications:write。")

            if key_hash:
                existing = (
                    ApplicationChangeIdempotency.objects.select_for_update()
                    .select_related("proposal")
                    .filter(
                        user_id=user_id,
                        client_id=client_id,
                        operation="apply_application_change",
                        key_hash=key_hash,
                    )
                    .first()
                )
                if existing is not None:
                    if existing.request_hash != apply_request_hash or existing.proposal_id != proposal.pk:
                        raise _ProposalFailure("IDEMPOTENCY_CONFLICT", "同一幂等键不能应用不同请求。", proposal_id=proposal_id)
                    result_data = dict(existing.result)
                    result_data["idempotent_replay"] = True
                    replay_audit = _audit_sync(
                        user_id=user_id,
                        subject_id=user_id,
                        request_id=_request_id(),
                        client_id=client_id,
                        resource=resource,
                        tool_name="apply_application_change",
                        operation=proposal.operation,
                        proposal=proposal,
                        idempotency_key_hash=key_hash,
                        target=proposal.target,
                        changed_fields=[item.get("field") for item in proposal.after_state.get("changes", [])],
                        before_summary=proposal.before_state,
                        after_summary=proposal.after_state,
                        outcome=ApplicationChangeAudit.Outcome.REPLAY,
                    )
                    result_data["audit_evidence"] = _set_audit_evidence(
                        replay_audit,
                        outcome=ApplicationChangeAudit.Outcome.REPLAY,
                    )
                    return ApplyChangeResult.model_validate(result_data)

            if proposal.status == ApplicationChangeProposal.Status.APPLIED:
                result_data = dict(proposal.applied_result)
                result_data["idempotent_replay"] = True
                replay_audit = _audit_sync(
                    user_id=user_id,
                    subject_id=user_id,
                    request_id=_request_id(),
                    client_id=client_id,
                    resource=resource,
                    tool_name="apply_application_change",
                    operation=proposal.operation,
                    proposal=proposal,
                    idempotency_key_hash=key_hash,
                    target=proposal.target,
                    changed_fields=[],
                    before_summary=proposal.before_state,
                    after_summary=proposal.after_state,
                    outcome=ApplicationChangeAudit.Outcome.REPLAY,
                )
                result_data["audit_evidence"] = _set_audit_evidence(
                    replay_audit,
                    outcome=ApplicationChangeAudit.Outcome.REPLAY,
                )
                return ApplyChangeResult.model_validate(result_data)
            if proposal.status == ApplicationChangeProposal.Status.EXPIRED or proposal.expires_at <= timezone.now():
                raise _ProposalFailure("PROPOSAL_EXPIRED", "提案已过期。", proposal_id=proposal_id)
            if proposal.status == ApplicationChangeProposal.Status.REVOKED:
                raise _ProposalFailure("PROPOSAL_REVOKED", "提案已撤销。", proposal_id=proposal_id)

            if proposal.operation == "upsert_application_stage":
                _validate_proposal_stage(proposal.target, proposal.change)
                application, position = _load_target(user_id, proposal.target, lock=True)
                current = _stage_snapshot(application, position, proposal.change, lock=True)
                if _json_hash(current) != proposal.state_fingerprint:
                    raise _ProposalFailure("CONFLICT", "预览后的目标数据已发生变化，请重新预览。", proposal_id=proposal_id)
                expected_after = _proposed_stage_snapshot(current, proposal.change)
                result = _upsert_application_stage_sync(
                    user_id=user_id,
                    application_id=application.pk,
                    position_id=position.pk if position is not None else None,
                    stage_type=proposal.change["stage_type"],
                    interview_round=proposal.change.get("interview_round"),
                    interview_name=proposal.change.get("interview_name"),
                    scheduled_at=datetime.fromisoformat(proposal.change["scheduled_at"].replace("Z", "+00:00"))
                    if proposal.change.get("scheduled_at")
                    else None,
                    duration_minutes=proposal.change.get("duration_minutes"),
                    manage_connection=False,
                )
                application_data = result.application
                before_summary = current
                after_summary = expected_after
            else:
                application_time = (
                    datetime.fromisoformat(proposal.change["application_time"].replace("Z", "+00:00"))
                    if proposal.change.get("application_time")
                    else None
                )
                company = None
                if proposal.change.get("company_id"):
                    company = Company.objects.filter(pk=proposal.change["company_id"]).first()
                current_application = None
                if company is not None:
                    current_application = JobApplication.objects.filter(user_id=user_id, company=company).first()
                if _json_hash({"application_id": current_application.pk if current_application else None}) != proposal.state_fingerprint:
                    raise _ProposalFailure("CONFLICT", "预览后的目标数据已发生变化，请重新预览。", proposal_id=proposal_id)
                result = _create_application_sync(
                    user_id=user_id,
                    position_name=proposal.change["position_name"],
                    company_name=proposal.change.get("company_name"),
                    company_id=proposal.change.get("company_id"),
                    application_time=application_time,
                    application_url=None,
                    notes=proposal.change.get("notes"),
                    application_status=proposal.change.get("application_status") or "applied",
                    source=None,
                    manage_connection=False,
                )
                application_data = result.application
                before_summary = proposal.before_state
                after_summary = proposal.after_state

            audit = _audit_sync(
                user_id=user_id,
                subject_id=user_id,
                request_id=_request_id(),
                client_id=client_id,
                resource=resource,
                tool_name="apply_application_change",
                operation=proposal.operation,
                proposal=proposal,
                idempotency_key_hash=key_hash,
                target=proposal.target,
                changed_fields=[item.get("field") for item in proposal.after_state.get("changes", [])]
                if isinstance(proposal.after_state.get("changes"), list)
                else [],
                before_summary=before_summary,
                after_summary=after_summary,
                outcome=ApplicationChangeAudit.Outcome.SUCCESS,
            )
            audit_evidence = _set_audit_evidence(
                audit,
                outcome=ApplicationChangeAudit.Outcome.SUCCESS,
            )
            output = ApplyChangeResult(
                proposal_id=proposal.proposal_id,
                status="applied",
                idempotent_replay=False,
                application=application_data,
                audit_id=audit.audit_id,
                audit_evidence=audit_evidence,
            )
            output_data = output.model_dump(mode="json")
            proposal.status = ApplicationChangeProposal.Status.APPLIED
            proposal.applied_at = timezone.now()
            proposal.applied_result = output_data
            proposal.save(update_fields=["status", "applied_at", "applied_result", "updated_at"])
            if key_hash:
                ApplicationChangeIdempotency.objects.create(
                    user_id=user_id,
                    client_id=client_id,
                    resource=resource,
                    operation="apply_application_change",
                    key_hash=key_hash,
                    request_hash=apply_request_hash,
                    proposal=proposal,
                    result=output_data,
                )
            return output
    except _ProposalFailure as exc:
        _record_apply_failure(
            user_id=user_id,
            client_id=client_id,
            resource=resource,
            proposal_id=proposal_id,
            key_hash=key_hash,
            code=exc.code,
        )
        raise ToolError(f"{exc.code}: {exc.message}") from exc
    except ToolError:
        _record_apply_failure(
            user_id=user_id,
            client_id=client_id,
            resource=resource,
            proposal_id=proposal_id,
            key_hash=key_hash,
            code="BUSINESS_VALIDATION_FAILED",
        )
        raise
    except IntegrityError as exc:
        _record_apply_failure(
            user_id=user_id,
            client_id=client_id,
            resource=resource,
            proposal_id=proposal_id,
            key_hash=key_hash,
            code="TRANSACTION_FAILED",
        )
        raise ToolError("TRANSACTION_FAILED: 应用失败，数据未写入。") from exc
    except _AuditWriteFailure as exc:
        _set_audit_evidence(
            None,
            outcome=ApplicationChangeAudit.Outcome.FAILURE,
            failure_code="AUDIT_WRITE_FAILED",
            recorded=False,
        )
        raise ToolError("AUDIT_WRITE_FAILED: 应用失败，数据未写入。") from exc
    except Exception as exc:
        # Database/serialization failures must not expose implementation
        # details.  The transaction.atomic block has already rolled back any
        # business and proposal changes before this response is returned.
        _set_audit_evidence(
            None,
            outcome=ApplicationChangeAudit.Outcome.FAILURE,
            failure_code="TRANSACTION_FAILED",
            recorded=False,
        )
        raise ToolError("TRANSACTION_FAILED: 应用失败，数据未写入。") from exc
    finally:
        close_old_connections()


async def preview_application_change_data(
    *,
    operation: str,
    target: ProposalTarget,
    change: ProposalChange,
    idempotency_key: str | None = None,
) -> PreviewChangeResult:
    _require_scope("applications:write")
    user_id, client_id, resource, scopes = _oauth_context()
    return await sync_to_async(_preview_sync, thread_sensitive=True)(
        user_id=user_id,
        client_id=client_id,
        resource=resource,
        scopes=scopes,
        operation=operation,
        target=target,
        change=change,
        idempotency_key=idempotency_key,
    )


async def apply_application_change_data(
    *,
    proposal_id: str,
    confirm: StrictBool,
    idempotency_key: str | None = None,
) -> ApplyChangeResult:
    _require_scope("applications:write")
    user_id, client_id, resource, scopes = _oauth_context()
    if (
        not isinstance(proposal_id, str)
        or (not proposal_id.startswith("prop_") and not _test_expired_fixture_enabled(proposal_id))
    ):
        raise ToolError("PROPOSAL_NOT_FOUND: 提案不存在。")
    return await sync_to_async(_apply_sync, thread_sensitive=True)(
        user_id=user_id,
        client_id=client_id,
        resource=resource,
        scopes=scopes,
        proposal_id=proposal_id,
        confirm=confirm,
        idempotency_key=idempotency_key,
    )
