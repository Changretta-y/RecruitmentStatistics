"""MCP-003 acceptance-gap black-box evidence.

This file deliberately uses only the public MCP endpoint and the existing
public OAuth fixture helpers.  It records what can and cannot be proven
without a public audit query or fault-injection surface.
"""

from __future__ import annotations

import os

import pytest
from django.test import Client

from tests import test_mcp_003 as mcp003


pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def proposal_users():
    # Reuse the already-verified public OAuth setup without importing any
    # production module or relying on a process-local proposal cache.
    return mcp003.proposal_users.__wrapped__()


def _json(response):
    assert response["Content-Type"].startswith("application/json"), response.content
    return response.json()


def _call(client, token, name, arguments):
    return mcp003._mcp(
        client,
        "tools/call",
        {"name": name, "arguments": arguments},
        token=token,
    )


def _create(client, token, company):
    response = _call(
        client,
        token,
        "create_application",
        {"company_name": company, "position_name": "后端", "application_status": "applied"},
    )
    assert response.status_code == 200, response.content
    result = _json(response)["result"]
    assert result.get("isError") is not True, response.content
    return result["structuredContent"]["application"]


def _preview(client, token, application, key):
    response = _call(
        client,
        token,
        "preview_application_change",
        {
            "operation": "upsert_application_stage",
            "target": {
                "application_id": application["id"],
                "position_id": application["positions"][0]["id"],
            },
            "change": {
                "stage_type": "interview",
                "interview_round": "second",
                "interview_name": "二面",
                "scheduled_at": "2026-11-01T14:00:00+08:00",
                "duration_minutes": 60,
            },
            "idempotency_key": key,
        },
    )
    assert response.status_code == 200, response.content
    result = _json(response)["result"]
    assert result.get("isError") is not True, response.content
    return result["structuredContent"]


def test_proposal_survives_independent_http_clients_without_protocol_session(proposal_users):
    """A fresh Client must be able to apply a proposal created by another request."""

    token = proposal_users[0]["mcp_access"]
    preview_client = Client()
    apply_client = Client()
    application = _create(preview_client, token, "MCP-003 独立客户端公司")
    proposal = _preview(preview_client, token, application, "acceptance-stateless")

    applied = _call(
        apply_client,
        token,
        "apply_application_change",
        {
            "proposal_id": proposal["proposal_id"],
            "confirm": True,
            "idempotency_key": "acceptance-stateless-apply",
        },
    )
    assert applied.status_code == 200, applied.content
    result = _json(applied)["result"]
    assert result.get("isError") is not True, applied.content
    assert result["structuredContent"]["status"] == "applied"


def test_public_results_cover_audit_id_and_redaction_for_success_replay_failure_and_conflict(proposal_users):
    token = proposal_users[0]["mcp_access"]
    client = Client()

    # Success: public evidence is the audit_id and the applied result.
    application = _create(client, token, "MCP-003 审计证据公司")
    proposal = _preview(client, token, application, "audit-success")
    success = _call(
        client,
        token,
        "apply_application_change",
        {"proposal_id": proposal["proposal_id"], "confirm": True, "idempotency_key": "audit-success-apply"},
    )
    success_body = _json(success)
    assert success_body["result"]["structuredContent"]["audit_id"]

    # Replay: public result must identify the replay without returning secrets.
    replay = _call(
        Client(),
        token,
        "apply_application_change",
        {"proposal_id": proposal["proposal_id"], "confirm": True, "idempotency_key": "audit-success-apply"},
    )
    replay_body = _json(replay)
    assert replay_body["result"]["structuredContent"]["idempotent_replay"] is True
    assert replay_body["result"]["structuredContent"]["audit_id"] == success_body["result"]["structuredContent"]["audit_id"]

    # confirm=false: no business write and no credential disclosure.
    application = _create(client, token, "MCP-003 审计失败证据公司")
    proposal = _preview(client, token, application, "audit-confirm-false")
    rejected = _call(
        Client(),
        token,
        "apply_application_change",
        {"proposal_id": proposal["proposal_id"], "confirm": False},
    )
    rejected_text = rejected.content.decode(errors="replace").lower()
    assert _json(rejected)["result"].get("isError") is True
    assert "audit-success-apply" not in rejected_text

    # Conflict: the newer direct MCP-002 write must remain observable.
    position_id = application["positions"][0]["id"]
    changed = _call(
        client,
        token,
        "upsert_application_stage",
        {
            "application_id": application["id"],
            "position_id": position_id,
            "stage_type": "interview",
            "interview_round": "second",
            "interview_name": "二面",
            "scheduled_at": "2026-11-02T14:00:00+08:00",
            "duration_minutes": 45,
        },
    )
    assert _json(changed)["result"].get("isError") is not True
    conflict = _call(
        Client(),
        token,
        "apply_application_change",
        {"proposal_id": proposal["proposal_id"], "confirm": True, "idempotency_key": "audit-conflict"},
    )
    conflict_text = conflict.content.decode(errors="replace")
    assert _json(conflict)["result"].get("isError") is True
    assert "CONFLICT" in conflict_text.upper()
    for secret in (token, "authorization_code", "refresh_token", "password", "SELECT "):
        assert secret.lower() not in conflict_text.lower()


def test_expired_proposal_can_be_checked_when_public_test_surface_is_available(proposal_users):
    """Use only an explicitly provided public test proposal; never alter DB state."""

    expired_id = os.environ.get("MCP_TEST_EXPIRED_PROPOSAL_ID")
    if not expired_id:
        pytest.skip(
            "公开契约未提供可控过期 proposal 或测试时钟入口；最小夹具需提供已过期 proposal_id，"
            "或提供仅测试环境的短 TTL/clock 控制，不得修改生产数据。"
        )
    response = _call(
        Client(),
        proposal_users[0]["mcp_access"],
        "apply_application_change",
        {"proposal_id": expired_id, "confirm": True},
    )
    assert response.status_code == 200
    text = response.content.decode(errors="replace").upper()
    assert "PROPOSAL_EXPIRED" in text
    assert expired_id not in response.content.decode(errors="replace")


def test_audit_failure_injection_rolls_back_when_public_test_surface_is_available(proposal_users):
    """Require an explicit test-only public switch; do not invent an internal hook."""

    if os.environ.get("MCP_TEST_AUDIT_FAILURE_MODE") != "1":
        pytest.skip(
            "当前公开契约没有审计写入故障注入入口；最小夹具需提供仅测试环境的公开故障开关，"
            "使 audit write 失败并可观察业务数据、proposal 消费均未发生。"
        )
    token = proposal_users[0]["mcp_access"]
    client = Client()
    application = _create(client, token, "MCP-003 审计故障回滚公司")
    proposal = _preview(client, token, application, "audit-failure-rollback")
    response = _call(
        Client(),
        token,
        "apply_application_change",
        {"proposal_id": proposal["proposal_id"], "confirm": True, "idempotency_key": "audit-failure-apply"},
    )
    assert response.status_code == 200
    result = _json(response)["result"]
    assert result.get("isError") is True
    assert "AUDIT" in response.content.decode(errors="replace").upper()
    readback = _call(client, token, "find_applications", {"application_id": application["id"]})
    data = _json(readback)["result"]["structuredContent"]["results"][0]
    assert data["positions"][0]["interviews"] == []
