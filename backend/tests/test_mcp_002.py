"""MCP-002 black-box RED tests for OAuth write tools.

Only public registration, OAuth, HTTP/JSON-RPC and public REST setup endpoints
are used.  No production module, model, serializer, URL configuration or MCP
implementation is imported.
"""

from __future__ import annotations

import uuid
from urllib.parse import parse_qs, urlencode, urlparse

import pytest
from django.test import Client

from tests import test_mcp_001 as mcp001


pytestmark = pytest.mark.django_db(transaction=True)


WRITE_SCOPE = "applications:write"
READ_SCOPE = "applications:read"
MCP_URL = mcp001.MCP_URL
MCP_RESOURCE = mcp001.MCP_RESOURCE
AUTHORIZE_URL = mcp001.AUTHORIZE_URL
TOKEN_URL = mcp001.TOKEN_URL


def _json(response):
    assert response["Content-Type"].startswith("application/json"), response.content
    return response.json()


def _mcp(client, method, params=None, *, token):
    return mcp001._mcp_request(client, method, params, token=token)


def _authorize_scope(web_client, *, client_id, redirect_uri, credentials, scope):
    verifier, challenge = mcp001._pkce_pair(scope)
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": "mcp-002-state",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "resource": MCP_RESOURCE,
    }
    query = urlencode(params)
    response = web_client.get(f"{AUTHORIZE_URL}?{query}", follow=False)
    assert response.status_code in {200, 302, 303}, response.content
    if response.status_code in {302, 303}:
        parsed = urlparse(response["Location"])
        returned = parse_qs(parsed.query)
        assert returned.get("state") == ["mcp-002-state"]
        assert returned.get("code"), response.content
        code = returned["code"][0]
    else:
        parser = mcp001._FormParser()
        parser.feed(response.content.decode(errors="replace"))
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
        assert returned.get("state") == ["mcp-002-state"]
        assert returned.get("code"), approved.content
        code = returned["code"][0]

    token_response = web_client.post(
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
    assert token_response.status_code == 200, token_response.content
    body = _json(token_response)
    assert body["token_type"].lower() == "bearer"
    assert WRITE_SCOPE in body["scope"]
    assert body["access_token"]
    return body["access_token"]


@pytest.fixture
def write_users():
    users = []
    for prefix in ("mcp-write-a", "mcp-write-b"):
        web_client, credentials, web_access = mcp001._register_web_user(prefix)
        redirect_uri = f"https://{prefix}.example.test/callback"
        client_id = mcp001._register_dcr_client(web_client, redirect_uri)
        try:
            token = _authorize_scope(
                web_client,
                client_id=client_id,
                redirect_uri=redirect_uri,
                credentials=credentials,
                scope=f"{READ_SCOPE} {WRITE_SCOPE}",
            )
        except AssertionError as error:
            # Keep the public HTTP tests runnable against the MCP-001 baseline:
            # before write-scope support exists, use a real read-only token so
            # each write assertion fails at the missing behavior boundary
            # instead of failing in fixture construction.
            assert "invalid_scope" in str(error), error
            verifier, challenge = mcp001._pkce_pair(f"fallback-{prefix}")
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
                "prefix": prefix,
            }
        )
    return users


@pytest.fixture
def read_only_user():
    web_client, credentials, web_access = mcp001._register_web_user("mcp-read-only")
    redirect_uri = "https://mcp-read-only.example.test/callback"
    client_id = mcp001._register_dcr_client(web_client, redirect_uri)
    verifier, challenge = mcp001._pkce_pair("read-only")
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


def _public_company(web_access, name):
    client = Client()
    response = client.post(
        mcp001.COMPANIES_URL,
        {"company_name": name, "recruitment_url": None},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {web_access}",
    )
    assert response.status_code == 201, response.content
    return _json(response)["id"]


def _public_application(web_access, company_id, position_name, *, status="applied"):
    client = Client()
    response = client.post(
        mcp001.APPLICATIONS_URL,
        {
            "company_id": company_id,
            "positions": [
                {
                    "position_name": position_name,
                    "application_status": status,
                    "application_time": None,
                    "notes": "MCP-002 fixture",
                    "interviews": [],
                }
            ],
            "shared_stages": [],
        },
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {web_access}",
    )
    assert response.status_code == 201, response.content
    return _json(response)


def _call(token, name, arguments):
    return _mcp(Client(), "tools/call", {"name": name, "arguments": arguments}, token=token)


def test_write_scope_is_discovered_and_tools_list_has_exact_write_whitelist(client, write_users):
    metadata = client.get(mcp001.PROTECTED_RESOURCE_METADATA_URL)
    assert metadata.status_code == 200
    assert set(_json(metadata)["scopes_supported"]) >= {READ_SCOPE, WRITE_SCOPE}

    metadata = client.get(mcp001.AUTHORIZATION_SERVER_METADATA_URL)
    assert metadata.status_code == 200
    assert set(_json(metadata)["scopes_supported"]) >= {READ_SCOPE, WRITE_SCOPE}

    response = _mcp(client, "tools/list", token=write_users[0]["mcp_access"])
    assert response.status_code == 200, response.content
    names = [item["name"] for item in _json(response)["result"]["tools"]]
    assert names == ["find_applications", "create_application", "upsert_application_stage"]
    tools = {item["name"]: item for item in _json(response)["result"]["tools"]}
    assert tools["find_applications"]["annotations"]["readOnlyHint"] is True
    assert tools["create_application"]["annotations"]["readOnlyHint"] is False
    assert tools["upsert_application_stage"]["annotations"]["readOnlyHint"] is False
    assert {"company_name", "company_id", "position_name"} <= set(
        tools["create_application"]["inputSchema"]["properties"]
    )
    assert {"application_id", "stage_type", "scheduled_at"} <= set(
        tools["upsert_application_stage"]["inputSchema"]["properties"]
    )


def test_read_token_cannot_call_write_tools(read_only_user):
    response = _call(
        read_only_user["mcp_access"],
        "create_application",
        {"company_name": "不应写入", "position_name": "后端"},
    )
    assert response.status_code == 403, response.content
    assert "insufficient_scope" in response.content.decode(errors="replace")


def test_create_application_new_company_returns_public_structured_aggregate(write_users):
    response = _call(
        write_users[0]["mcp_access"],
        "create_application",
        {
            "company_name": "MCP 新公司",
            "position_name": "后端开发",
            "application_time": "2026-10-11T10:00:00+08:00",
            "application_status": "applied",
            "notes": "来自邮件的结构化描述",
            "source": {"type": "email", "id": "mail-mcp-002-1"},
        },
    )
    assert response.status_code == 200, response.content
    result = _json(response)["result"]
    assert result.get("isError") is not True
    data = result["structuredContent"]
    assert result["content"]
    assert data["created"] is True
    assert data["position_created"] is True
    assert data["application"]["company_name"] == "MCP 新公司"
    assert data["application"]["positions"][0]["position_name"] == "后端开发"
    assert "user_id" not in data["application"]


def test_create_application_reuses_company_appends_position_and_duplicate_is_deterministic(write_users):
    token = write_users[0]["mcp_access"]
    first = _json(_call(token, "create_application", {"company_name": "复用公司", "position_name": "后端"}))["result"]["structuredContent"]
    second = _json(_call(token, "create_application", {"company_name": "  复用公司 ", "position_name": "数据"}))["result"]["structuredContent"]
    duplicate = _json(_call(token, "create_application", {"company_name": "复用公司", "position_name": "后端"}))["result"]["structuredContent"]
    assert second["application"]["company_id"] == first["application"]["company_id"]
    assert {p["position_name"] for p in second["application"]["positions"]} == {"后端", "数据"}
    assert duplicate["position_created"] is False
    assert len(duplicate["application"]["positions"]) == 2


def test_create_application_rejects_invalid_inputs_atomically(write_users):
    token = write_users[0]["mcp_access"]
    invalid_payloads = [
        {"position_name": "缺公司"},
        {"company_name": "非法状态公司", "position_name": "后端", "application_status": "in_progress"},
        {"company_name": "无时区公司", "position_name": "后端", "application_time": "2026-10-11T10:00:00"},
        {"company_name": "岗位 URL 公司", "position_name": "后端", "application_url": "https://jobs.example.test"},
        {"company_name": "空岗位公司", "position_name": "  "},
        {"company_name": "伪造用户公司", "position_name": "后端", "user_id": 999999},
    ]
    expected_markers = ("company", "application_status", "application_time", "application_url", "position_name", "user_id")
    for payload, marker in zip(invalid_payloads, expected_markers):
        response = _call(token, "create_application", payload)
        assert response.status_code == 200, response.content
        body = _json(response)["result"]
        assert body.get("isError") is True or "error" in body
        text = response.content.decode(errors="replace")
        assert marker in text
        assert "Unknown tool" not in text
        assert "Traceback" not in text

    lookup = _call(token, "find_applications", {"company_name": "非法状态公司"})
    assert _json(lookup)["result"]["structuredContent"]["results"] == []


def test_upsert_shared_assessment_and_written_test_add_update_clear_preserves_status(write_users):
    token = write_users[0]["mcp_access"]
    created = _json(_call(token, "create_application", {"company_name": "流程公司", "position_name": "后端", "application_status": "applied"}))["result"]["structuredContent"]["application"]
    app_id = created["id"]
    position_id = created["positions"][0]["id"]
    for stage_type, expected in (("assessment", "assessment"), ("written_test", "written_test")):
        add = _json(_call(token, "upsert_application_stage", {"application_id": app_id, "stage_type": stage_type, "scheduled_at": "2026-10-15T19:00:00+08:00", "duration_minutes": 120}))["result"]
        assert add["structuredContent"]["updated_stage"]["type"] == stage_type
        assert add["structuredContent"]["current_stage"] == expected
        update = _json(_call(token, "upsert_application_stage", {"application_id": app_id, "stage_type": stage_type, "scheduled_at": "2026-10-16T19:00:00+08:00", "duration_minutes": 90}))["result"]["structuredContent"]
        assert update["updated_stage"]["duration_minutes"] == 90
        assert update["application"]["positions"][0]["application_status"] == "applied"
        clear = _json(_call(token, "upsert_application_stage", {"application_id": app_id, "stage_type": stage_type, "scheduled_at": None, "duration_minutes": None}))["result"]["structuredContent"]
        assert clear["updated_stage"]["scheduled_at"] is None
        assert clear["updated_stage"]["duration_minutes"] is None
    assert position_id in {p["id"] for p in created["positions"]}


def test_upsert_interviews_supports_rounds_custom_name_update_and_clear(write_users):
    token = write_users[0]["mcp_access"]
    created = _json(_call(token, "create_application", {"company_name": "面试公司", "position_name": "后端"}))["result"]["structuredContent"]["application"]
    app_id, position_id = created["id"], created["positions"][0]["id"]
    stages = [("first", "一面"), ("second", "二面"), ("third", "三面"), ("hr", "HR 面"), ("other", "终面")]
    for round_name, interview_name in stages:
        result = _json(_call(token, "upsert_application_stage", {"application_id": app_id, "position_id": position_id, "stage_type": "interview", "interview_round": round_name, "interview_name": interview_name, "scheduled_at": "2026-10-20T14:00:00+08:00", "duration_minutes": 60}))["result"]
        assert result["structuredContent"]["updated_stage"]["name"] == interview_name
    updated = _json(_call(token, "upsert_application_stage", {"application_id": app_id, "position_id": position_id, "stage_type": "interview", "interview_round": "second", "interview_name": "二面", "scheduled_at": "2026-10-21T14:00:00+08:00", "duration_minutes": 75}))["result"]["structuredContent"]
    assert updated["updated_stage"]["duration_minutes"] == 75
    cleared = _json(_call(token, "upsert_application_stage", {"application_id": app_id, "position_id": position_id, "stage_type": "interview", "interview_round": "second", "interview_name": "二面", "scheduled_at": None, "duration_minutes": None}))["result"]["structuredContent"]
    assert cleared["updated_stage"]["scheduled_at"] is None
    assert cleared["updated_stage"]["duration_minutes"] is None


def test_upsert_rejects_bad_stage_datetime_duration_and_target_without_partial_write(write_users):
    token = write_users[0]["mcp_access"]
    created = _json(_call(token, "create_application", {"company_name": "非法流程公司", "position_name": "后端"}))["result"]["structuredContent"]["application"]
    app_id, position_id = created["id"], created["positions"][0]["id"]
    bad = [
        {"application_id": app_id, "stage_type": "phone_screen", "scheduled_at": None},
        {"application_id": app_id, "stage_type": "assessment", "scheduled_at": "2026-10-20T14:00:00", "duration_minutes": 60},
        {"application_id": app_id, "stage_type": "written_test", "scheduled_at": "2026-10-20T14:00:00+08:00", "duration_minutes": 0},
        {"application_id": app_id, "position_id": position_id + 999999, "stage_type": "interview", "interview_round": "first", "scheduled_at": None},
    ]
    for payload in bad:
        response = _call(token, "upsert_application_stage", payload)
        assert response.status_code == 200, response.content
        result = _json(response)["result"]
        assert result.get("isError") is True
        assert "Unknown tool" not in response.content.decode(errors="replace")
    readback = _json(_call(token, "find_applications", {"application_id": app_id}))["result"]["structuredContent"]["results"][0]
    assert readback["shared_stages"] == []
    assert readback["positions"][0]["interviews"] == []


def test_write_tools_enforce_cross_user_isolation_and_no_user_override(write_users):
    first, second = write_users
    created = _json(_call(first["mcp_access"], "create_application", {"company_name": "隔离公司", "position_name": "A 岗"}))["result"]["structuredContent"]["application"]
    app_id, position_id = created["id"], created["positions"][0]["id"]
    foreign_create = _call(second["mcp_access"], "create_application", {"company_id": created["company_id"], "position_name": "B 岗", "user_id": first["prefix"]})
    assert foreign_create.status_code == 200
    assert _json(foreign_create)["result"].get("isError") is True
    assert "Unknown tool" not in foreign_create.content.decode(errors="replace")
    for payload in (
        {"application_id": app_id, "stage_type": "assessment", "scheduled_at": None},
        {"application_id": app_id, "position_id": position_id, "stage_type": "interview", "interview_round": "first", "scheduled_at": None},
    ):
        response = _call(second["mcp_access"], "upsert_application_stage", payload)
        assert response.status_code == 200
        result = _json(response)["result"]
        assert result.get("isError") is True or "404" in response.content.decode(errors="replace")
        assert "Unknown tool" not in response.content.decode(errors="replace")


def test_create_application_rejects_inconsistent_company_id_and_name_without_partial_write(write_users):
    token = write_users[0]["mcp_access"]
    first = _json(_call(token, "create_application", {"company_name": "一致性公司", "position_name": "后端"}))["result"]["structuredContent"]["application"]
    response = _call(token, "create_application", {"company_id": first["company_id"] + 999999, "company_name": "一致性公司", "position_name": "不应写入"})
    assert response.status_code == 200
    assert _json(response)["result"].get("isError") is True
    assert "Unknown tool" not in response.content.decode(errors="replace")
    readback = _json(_call(token, "find_applications", {"application_id": first["id"]}))["result"]["structuredContent"]["results"][0]
    assert [p["position_name"] for p in readback["positions"]] == ["后端"]

