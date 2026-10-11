"""Persistent state for the MCP write-confirmation workflow.

These models intentionally contain only normalized, redacted proposal and
audit data.  OAuth credentials and free-form source messages never enter the
MCP database.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


def _proposal_id() -> str:
    return f"prop_{uuid.uuid4().hex}"


def _audit_id() -> str:
    return f"audit_{uuid.uuid4().hex}"


class ApplicationChangeProposal(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending_confirmation", "待确认"
        APPLIED = "applied", "已应用"
        EXPIRED = "expired", "已过期"
        REVOKED = "revoked", "已撤销"

    proposal_id = models.CharField(max_length=80, unique=True, default=_proposal_id)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    client_id = models.CharField(max_length=500)
    resource = models.CharField(max_length=500)
    scopes = models.JSONField(default=list)
    operation = models.CharField(max_length=80)
    target = models.JSONField(default=dict)
    change = models.JSONField(default=dict)
    before_state = models.JSONField(default=dict)
    after_state = models.JSONField(default=dict)
    state_fingerprint = models.CharField(max_length=64)
    request_hash = models.CharField(max_length=64)
    idempotency_key_hash = models.CharField(max_length=64, null=True, blank=True)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PENDING)
    expires_at = models.DateTimeField()
    applied_result = models.JSONField(default=dict)
    applied_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mcp_application_change_proposals"
        indexes = [
            models.Index(fields=["user", "client_id", "operation"]),
            models.Index(fields=["expires_at", "status"]),
            models.Index(fields=["idempotency_key_hash"]),
        ]


class ApplicationChangeIdempotency(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    client_id = models.CharField(max_length=500)
    resource = models.CharField(max_length=500)
    operation = models.CharField(max_length=80)
    key_hash = models.CharField(max_length=64)
    request_hash = models.CharField(max_length=64)
    proposal = models.ForeignKey(
        ApplicationChangeProposal,
        on_delete=models.CASCADE,
        related_name="idempotency_records",
    )
    result = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mcp_application_change_idempotency"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "client_id", "operation", "key_hash"],
                name="mcp_change_idempotency_unique",
            )
        ]
        indexes = [
            models.Index(fields=["user", "client_id", "key_hash"]),
        ]


class ApplicationChangeAudit(models.Model):
    class Outcome(models.TextChoices):
        SUCCESS = "success", "成功"
        FAILURE = "failure", "失败"
        CONFLICT = "conflict", "冲突"
        EXPIRED = "expired", "过期"
        REPLAY = "replay", "重放"

    audit_id = models.CharField(max_length=80, unique=True, default=_audit_id)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    subject_id = models.PositiveBigIntegerField()
    request_id = models.CharField(max_length=100)
    client_id = models.CharField(max_length=500)
    resource = models.CharField(max_length=500)
    tool_name = models.CharField(max_length=80)
    operation = models.CharField(max_length=80)
    proposal = models.ForeignKey(
        ApplicationChangeProposal,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audits",
    )
    idempotency_key_hash = models.CharField(max_length=64, null=True, blank=True)
    target = models.JSONField(default=dict)
    changed_fields = models.JSONField(default=list)
    before_summary = models.JSONField(default=dict)
    after_summary = models.JSONField(default=dict)
    outcome = models.CharField(max_length=16, choices=Outcome.choices)
    failure_code = models.CharField(max_length=80, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mcp_application_change_audits"
        indexes = [
            models.Index(fields=["subject_id", "created_at"]),
            models.Index(fields=["proposal", "created_at"]),
            models.Index(fields=["outcome", "created_at"]),
        ]
