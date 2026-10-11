"""MCP-003 black-box tests for the proposal/confirmation safety loop."""

from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import parse_qs, urlencode, urlparse

import pytest
from django.test import Client

from tests import test_mcp_001 as mcp001
from tests import test_mcp_002 as mcp002


pytestmark = pytest.mark.django_db(transaction=True)

WRITE_SCOPE = "applications:write"
MCP_URL = mcp001.MCP_URL
MCP_RESOURCE = mcp001.MCP_RESOURCE
AUTHORIZE_URL = mcp001.AUTHORIZE_URL
TOKEN_URL = mcp001.TOKEN_URL


def _json(response):
    assert response["Content-Type"].startswith("application/json"), response.content
    return response.json()


def _mcp(client, method, params=None, *, token):
    return mcp001._mcp_request(client, method, params, token=token)


def _authorize_write(web_client, *, client_id, redirect_uri, scope):
    verifier, challenge = mcp001._pkce_pair(f"mcp003-{scope}")
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": "mcp-003-state",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "resource": MCP_RESOURCE,
    }
    query = urlencode(params)
    authorize = web_client.get(f"{AUTHORIZE_URL}?{query}", follow=False)
    assert authorize.status_code in {200, 302, 303}, authorize.content
    if authorize.status_code in {302, 303}:
        returned = parse_qs(urlparse(authorize["Location"]).query)
        assert returned.get("state") == ["mcp-003-state"]
        code = returned["code"][0]
    else:
        parser = mcp001._FormParser()
        parser.feed(authorize.content.decode(errors="replace"))
        assert parser.action or parser.inputs
        action = parser.action or AUTHORIZE_URL
        if "?" not in action:
            action = f"{action}?{query}"
        payload = dict(parser.inputs)
        payload.update(params)
        payload["allow"] = "Authorize"
        approved = web_client.post(action, payload, follow=False)
        assert approved.status_code in {302, 303}, approved.content
        returned = parse_qs(urlparse(approved["Location"]).query)
        assert returned.get("state") == ["mcp-003-state"]
        code = returned["code"][0]
    exchanged = web_client.post(
        TOKEN_URL,
        urlencode(
            {
                "grant_type": "authorization_code",
                "code": code,
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "code_verifier": verifier,
                "resource": MCP_RESOURCE,
            }
        ),
        content_type="application/x-www-form-urlencoded",
    )
    assert exchanged.status_code == 200, exchanged.content
    body = _json(exchanged)
    assert WRITE_SCOPE in body["scope"]
    return body["access_token"]


@pytest.fixture
def proposal_users():
    users = []
    for prefix in ("mcp-proposal-a", "mcp-proposal-b"):
        web_client, credentials, web_access = mcp001._register_web_user(prefix)
        redirect_uri = f"https://{prefix}.example.test/callback"
        client_id = mcp001._register_dcr_client(web_client, redirect_uri)
        try:
            token = _authorize_write(
                web_client,
                client_id=client_id,
                redirect_uri=redirect_uri,
                scope="applications:read applications:write",
            )
        except AssertionError as error:
            # On the MCP-002 baseline keep the tests at the public behavior
            # boundary with a real read-only token; no internal token is made.
            assert "invalid_scope" in str(error), error
            verifier, challenge = mcp001._pkce_pair(f"mcp003-fallback-{prefix}")
            code = mcp001._authorize_with_public_login(
                web_client,
                client_id=client_id,
                redirect_uri=redirect_uri,
                verifier=verifier,
                challenge=challenge,
                credentials=credentials,
            )
            token = mcp001._exchange_code(
                web_client,
                client_id=client_id,
                redirect_uri=redirect_uri,
                code=code,
                verifier=verifier,
            )
        users.append(
            {
                "client": web_client,
                "web_access": web_access,
                "mcp_access": token,
                "client_id": client_id,
                "prefix": prefix,
            }
        )
    return users


@pytest.fixture
def read_only_user():
    web_client, credentials, web_access = mcp001._register_web_user("mcp003-read-only")
    redirect_uri = "https://mcp003-read-only.example.test/callback"
    client_id = mcp001._register_dcr_client(web_client, redirect_uri)
    verifier, challenge = mcp001._pkce_pair("mcp003-read-only")
    code = mcp001._authorize_with_public_login(
        web_client,
        client_id=client_id,
        redirect_uri=redirect_uri,
        verifier=verifier,
        challenge=challenge,
        credentials=credentials,
    )
    token = mcp001._exchange_code(
        web_client,
        client_id=client_id,
        redirect_uri=redirect_uri,
        code=code,
        verifier=verifier,
    )
    return {"mcp_access": token, "web_access": web_access}


def _call(token, name, arguments):
    return _mcp(Client(), "tools/call", {"name": name, "arguments": arguments}, token=token)


def _create_application(token, company, position="后端"):
    response = _call(
        token,
        "create_application",
        {"company_name": company, "position_name": position, "application_status": "applied"},
    )
    assert response.status_code == 200, response.content
    result = _json(response)["result"]
    assert result.get("isError") is not True, response.content
    return result["structuredContent"]["application"]


def _preview(token, app_id, position_id, *, key="mcp003-preview-1", when="2026-10-25T14:00:00+08:00"):
    return _call(
        token,
        "preview_application_change",
        {
            "operation": "upsert_application_stage",
            "target": {"application_id": app_id, "position_id": position_id},
            "change": {
                "stage_type": "interview",
                "interview_round": "second",
                "interview_name": "二面",
                "scheduled_at": when,
                "duration_minutes": 60,
            },
            "idempotency_key": key,
        },
    )


def _proposal_body(response):
    assert response.status_code == 200, response.content
    result = _json(response)["result"]
    assert result.get("isError") is not True, response.content
    assert "Unknown tool" not in response.content.decode(errors="replace")
    return result["structuredContent"]


def test_tools_list_has_only_semantic_preview_apply_and_requires_write_scope(proposal_users, read_only_user):
    listed = _mcp(Client(), "tools/list", token=proposal_users[0]["mcp_access"])
    assert listed.status_code == 200, listed.content
    tools = _json(listed)["result"]["tools"]
    assert [tool["name"] for tool in tools] == [
        "find_applications",
        "create_application",
        "upsert_application_stage",
        "preview_application_change",
        "apply_application_change",
    ]
    names = {tool["name"] for tool in tools}
    assert not names & {"proposal_list", "proposal_get", "audit_list", "raw_patch", "sql"}
    for name in ("preview_application_change", "apply_application_change"):
        schema = next(tool for tool in tools if tool["name"] == name)["inputSchema"]
        assert schema["type"] == "object"
        assert schema["properties"]

    denied_preview = _call(
        read_only_user["mcp_access"],
        "preview_application_change",
        {"operation": "upsert_application_stage", "target": {}, "change": {}},
    )
    assert denied_preview.status_code == 403, denied_preview.content
    assert "insufficient_scope" in denied_preview.content.decode(errors="replace")


def test_preview_returns_short_lived_proposal_diff_and_does_not_change_business_data(proposal_users):
    token = proposal_users[0]["mcp_access"]
    application = _create_application(token, "MCP-003 预览公司")
    app_id, position_id = application["id"], application["positions"][0]["id"]
    before = _json(_call(token, "find_applications", {"application_id": app_id}))["result"]["structuredContent"]["results"][0]

    proposal = _proposal_body(_preview(token, app_id, position_id))
    assert proposal["proposal_id"]
    assert proposal["status"] == "pending_confirmation"
    assert proposal["confirmation_required"] is True
    assert proposal["target"] == {"application_id": app_id, "position_id": position_id}
    assert proposal["changes"]
    assert "from" in proposal["changes"][0] and "to" in proposal["changes"][0]
    expires_at = datetime.fromisoformat(proposal["expires_at"].replace("Z", "+00:00"))
    assert expires_at > datetime.now(timezone.utc)
    assert (expires_at - datetime.now(timezone.utc)).total_seconds() <= 10 * 60

    after = _json(_call(token, "find_applications", {"application_id": app_id}))["result"]["structuredContent"]["results"][0]
    assert after == before


@pytest.mark.parametrize("confirm", [None, False, "true", "确认", 1])
def test_apply_requires_boolean_true_and_does_not_consume_or_write(proposal_users, confirm):
    token = proposal_users[0]["mcp_access"]
    application = _create_application(token, f"MCP-003 确认校验-{confirm}")
    proposal = _proposal_body(_preview(token, application["id"], application["positions"][0]["id"], key=f"confirm-{confirm}"))
    args = {"proposal_id": proposal["proposal_id"]}
    if confirm is not None:
        args["confirm"] = confirm
    response = _call(token, "apply_application_change", args)
    assert response.status_code == 200, response.content
    result = _json(response)["result"]
    assert result.get("isError") is True
    assert "Unknown tool" not in response.content.decode(errors="replace")
    readback = _json(_call(token, "find_applications", {"application_id": application["id"]}))["result"]["structuredContent"]["results"][0]
    assert readback["positions"][0]["interviews"] == []


def test_apply_success_is_single_use_and_same_idempotency_replays_original_result(proposal_users):
    token = proposal_users[0]["mcp_access"]
    application = _create_application(token, "MCP-003 幂等公司")
    proposal = _proposal_body(_preview(token, application["id"], application["positions"][0]["id"], key="preview-idempotency"))
    apply_args = {"proposal_id": proposal["proposal_id"], "confirm": True, "idempotency_key": "apply-idempotency-1"}
    first = _json(_call(token, "apply_application_change", apply_args))["result"]
    assert first.get("isError") is not True
    first_data = first["structuredContent"]
    assert first_data["status"] == "applied"
    assert first_data["idempotent_replay"] is False
    assert first_data["audit_id"]

    replay = _json(_call(token, "apply_application_change", apply_args))["result"]
    assert replay.get("isError") is not True
    replay_data = replay["structuredContent"]
    assert replay_data["status"] == "applied"
    assert replay_data["idempotent_replay"] is True
    assert replay_data["audit_id"] == first_data["audit_id"]

    readback = _json(_call(token, "find_applications", {"application_id": application["id"]}))["result"]["structuredContent"]["results"][0]
    interviews = readback["positions"][0]["interviews"]
    assert len(interviews) == 1
    assert interviews[0]["name"] == "二面"


def test_same_idempotency_key_with_different_fingerprint_is_rejected(proposal_users):
    token = proposal_users[0]["mcp_access"]
    application = _create_application(token, "MCP-003 幂等冲突公司")
    first = _proposal_body(_preview(token, application["id"], application["positions"][0]["id"], key="same-key"))
    second_response = _preview(token, application["id"], application["positions"][0]["id"], key="same-key", when="2026-10-26T14:00:00+08:00")
    assert second_response.status_code == 200
    result = _json(second_response)["result"]
    assert result.get("isError") is True or result["structuredContent"]["proposal_id"] == first["proposal_id"]
    assert "Unknown tool" not in second_response.content.decode(errors="replace")
    if result.get("isError") is True:
        assert "IDEMPOTENCY" in second_response.content.decode(errors="replace").upper() or "CONFLICT" in second_response.content.decode(errors="replace").upper()


def test_apply_rejects_conflict_and_preserves_newer_target_data(proposal_users):
    token = proposal_users[0]["mcp_access"]
    application = _create_application(token, "MCP-003 冲突公司")
    position_id = application["positions"][0]["id"]
    proposal = _proposal_body(_preview(token, application["id"], position_id, key="conflict-preview"))
    changed = _json(_call(token, "upsert_application_stage", {"application_id": application["id"], "position_id": position_id, "stage_type": "interview", "interview_round": "second", "interview_name": "二面", "scheduled_at": "2026-10-24T14:00:00+08:00", "duration_minutes": 45}))["result"]
    assert changed.get("isError") is not True

    applied = _call(token, "apply_application_change", {"proposal_id": proposal["proposal_id"], "confirm": True, "idempotency_key": "conflict-apply"})
    assert applied.status_code == 200, applied.content
    result = _json(applied)["result"]
    assert result.get("isError") is True
    text = applied.content.decode(errors="replace").upper()
    assert "CONFLICT" in text
    assert "Unknown tool" not in applied.content.decode(errors="replace")
    readback = _json(_call(token, "find_applications", {"application_id": application["id"]}))["result"]["structuredContent"]["results"][0]
    assert readback["positions"][0]["interviews"][0]["duration_minutes"] == 45


def test_proposal_isolated_by_user_and_client_and_fake_ids_are_not_enumerable(proposal_users):
    owner, other = proposal_users
    application = _create_application(owner["mcp_access"], "MCP-003 隔离公司")
    proposal = _proposal_body(_preview(owner["mcp_access"], application["id"], application["positions"][0]["id"], key="owner-only"))

    foreign = _call(other["mcp_access"], "apply_application_change", {"proposal_id": proposal["proposal_id"], "confirm": True, "idempotency_key": "foreign-apply"})
    assert foreign.status_code == 200
    result = _json(foreign)["result"]
    assert result.get("isError") is True
    assert "404" in foreign.content.decode(errors="replace") or "NOT_FOUND" in foreign.content.decode(errors="replace").upper()
    assert proposal["proposal_id"] not in foreign.content.decode(errors="replace")

    fake = _call(owner["mcp_access"], "apply_application_change", {"proposal_id": "prop_does_not_exist", "confirm": True})
    assert fake.status_code == 200
    assert _json(fake)["result"].get("isError") is True
    assert "prop_does_not_exist" not in fake.content.decode(errors="replace")


def test_audit_result_is_present_and_sensitive_credentials_are_not_exposed(proposal_users):
    token = proposal_users[0]["mcp_access"]
    application = _create_application(token, "MCP-003 审计公司")
    proposal = _proposal_body(_preview(token, application["id"], application["positions"][0]["id"], key="audit-key"))
    response = _call(token, "apply_application_change", {"proposal_id": proposal["proposal_id"], "confirm": True, "idempotency_key": "audit-apply"})
    assert response.status_code == 200, response.content
    body = _json(response)
    result = body["result"]
    assert result.get("isError") is not True
    structured = result["structuredContent"]
    assert structured["audit_id"]
    text = response.content.decode(errors="replace").lower()
    for secret in (token.lower(), "authorization_code", "password", "refresh_token", "select "):
        assert secret not in text
    assert "audit_list" not in text

