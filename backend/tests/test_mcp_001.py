"""MCP-001 black-box tests for the public OAuth/MCP contract.

The tests use only public HTTP/JSON-RPC endpoints.  They deliberately do not
import production models, views, serializers, URL modules, or MCP internals.
OAuth success-path credentials are created inside the isolated test database
through public registration, DCR, authorization, login, and token endpoints.
"""

from __future__ import annotations

import base64
import hashlib
import html
import uuid
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlencode, urlparse

import pytest
from django.test import Client


PROTECTED_RESOURCE_METADATA_URL = "/.well-known/oauth-protected-resource/mcp"
AUTHORIZATION_SERVER_METADATA_URL = "/.well-known/oauth-authorization-server"
AUTHORIZE_URL = "/oauth/authorize"
OAUTH_LOGIN_URL = "/oauth/login"
TOKEN_URL = "/oauth/token"
MCP_URL = "/mcp"
DCR_URL = "/oauth/register"
COMPANIES_URL = "/api/v1/companies/"
APPLICATIONS_URL = "/api/v1/applications/"

MCP_RESOURCE = "https://testserver/mcp"
MCP_ISSUER = "https://testserver"
CLIENT_METADATA_URL = "https://client.example.test/mcp-client.json"
REDIRECT_URI = "https://client.example.test/oauth/callback"

REGISTER_URL = "/api/v1/auth/register/"
LOGIN_URL = "/api/v1/auth/login/"
PASSWORD = "StrongPass_123"

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def client() -> Client:
    return Client()


def _json(response):
    assert response["Content-Type"].startswith("application/json"), response.content
    return response.json()


def _mcp_request(
    client: Client,
    method: str,
    params=None,
    *,
    token: str | None = None,
    session_id: str | None = None,
):
    headers = {
        "HTTP_ACCEPT": "application/json, text/event-stream",
        "HTTP_ORIGIN": "https://client.example.test",
    }
    if token is not None:
        headers["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    if session_id is not None:
        headers["HTTP_MCP_SESSION_ID"] = session_id
    return client.post(
        MCP_URL,
        {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": method,
            **({"params": params} if params is not None else {}),
        },
        content_type="application/json",
        **headers,
    )


def _oauth_authorize_query(**overrides):
    query = {
        "response_type": "code",
        "client_id": CLIENT_METADATA_URL,
        "redirect_uri": REDIRECT_URI,
        "scope": "applications:read",
        "state": "state-123",
        "code_challenge": "challenge-123",
        "code_challenge_method": "S256",
        "resource": MCP_RESOURCE,
    }
    query.update(overrides)
    return urlencode(query)


class _FormParser(HTMLParser):
    """Extract only public form action and input names from an OAuth page."""

    def __init__(self):
        super().__init__()
        self.action = ""
        self.inputs: dict[str, str] = {}

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "form" and not self.action:
            self.action = html.unescape(attributes.get("action", ""))
        if tag == "input" and attributes.get("name"):
            self.inputs[attributes["name"]] = attributes.get("value", "")


def _pkce_pair(seed: str) -> tuple[str, str]:
    verifier = f"mcp-verifier-{seed}-{uuid.uuid4().hex}"
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def _register_web_user(prefix: str) -> tuple[Client, dict[str, str], str]:
    web_client = Client()
    username = f"{prefix}-{uuid.uuid4().hex[:12]}"
    credentials = {
        "username": username,
        "email": f"{username}@example.test",
        "password": PASSWORD,
    }
    registered = web_client.post(
        REGISTER_URL,
        {**credentials, "password_confirm": PASSWORD},
        content_type="application/json",
    )
    assert registered.status_code == 201, registered.content
    logged_in = web_client.post(
        LOGIN_URL, credentials, content_type="application/json"
    )
    assert logged_in.status_code == 200, logged_in.content

    # The REST login above only supplies a Web JWT for public application
    # setup.  OAuth authorize uses the public Django session boundary, so
    # establish that session through the OAuth login form as a real client
    # would.  The hidden CSRF field is copied from the public form; the test
    # client does not enforce CSRF checks in this black-box suite.
    oauth_login_page = web_client.get(OAUTH_LOGIN_URL)
    assert oauth_login_page.status_code == 200, oauth_login_page.content
    login_form = _FormParser()
    login_form.feed(oauth_login_page.content.decode(errors="replace"))
    login_action = login_form.action or OAUTH_LOGIN_URL
    login_payload = dict(login_form.inputs)
    login_payload.update(
        {
            "username": credentials["username"],
            "password": credentials["password"],
            "next": "/",
        }
    )
    oauth_logged_in = web_client.post(login_action, login_payload, follow=False)
    assert oauth_logged_in.status_code in {200, 302, 303}, oauth_logged_in.content
    assert web_client.cookies.get("sessionid"), "公开 OAuth login 未建立 Django session"
    return web_client, credentials, logged_in.json()["access"]


def _register_dcr_client(web_client: Client, redirect_uri: str) -> str:
    response = web_client.post(
        DCR_URL,
        {
            "client_name": "MCP-001 public DCR test client",
            "redirect_uris": [redirect_uri],
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
        },
        content_type="application/json",
    )
    assert response.status_code in {200, 201}, response.content
    body = _json(response)
    assert body.get("client_id")
    return body["client_id"]


def _authorize_with_public_login(
    web_client: Client,
    *,
    client_id: str,
    redirect_uri: str,
    verifier: str,
    challenge: str,
    credentials: dict[str, str],
) -> str:
    authorize_params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "applications:read",
        "state": "dcr-state",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "resource": MCP_RESOURCE,
    }
    query = urlencode(authorize_params)
    authorize = web_client.get(f"{AUTHORIZE_URL}?{query}", follow=False)
    assert authorize.status_code in {200, 302, 303}, authorize.content

    if authorize.status_code in {302, 303}:
        location = authorize["Location"]
        parsed = urlparse(location)
        if parsed.path != urlparse(REDIRECT_URI).path:
            # If the public OAuth boundary still asks for login, submit its
            # own public form and return to the original full authorize URL.
            login_page = web_client.get(location, follow=False)
            assert login_page.status_code == 200, login_page.content
            login_form = _FormParser()
            login_form.feed(login_page.content.decode(errors="replace"))
            login_payload = dict(login_form.inputs)
            login_payload.update(
                {
                    "username": credentials["username"],
                    "password": credentials["password"],
                    "next": f"{AUTHORIZE_URL}?{query}",
                }
            )
            login_action = login_form.action or OAUTH_LOGIN_URL
            logged_in = web_client.post(login_action, login_payload, follow=False)
            assert logged_in.status_code in {302, 303}, logged_in.content
            authorize = web_client.get(f"{AUTHORIZE_URL}?{query}", follow=False)
            assert authorize.status_code == 200, authorize.content
        else:
            returned = parse_qs(parsed.query)
            assert returned.get("state") == ["dcr-state"]
            assert returned.get("code")
            return returned["code"][0]

    parser = _FormParser()
    parser.feed(authorize.content.decode(errors="replace"))
    assert parser.action or parser.inputs, "OAuth authorize page exposed no public form"
    form_action = parser.action or AUTHORIZE_URL
    if "?" not in form_action:
        form_action = f"{form_action}?{query}"
    form_payload = dict(parser.inputs)
    form_payload.update(authorize_params)
    # Django OAuth Toolkit's public consent form uses `allow`; accepting a
    # discovered `approve` field keeps this black-box fixture compatible with
    # equivalent public OAuth consent forms.
    if "allow" in form_payload:
        form_payload["allow"] = "Authorize"
    elif "approve" in form_payload:
        form_payload["approve"] = "Authorize"
    else:
        form_payload["allow"] = "Authorize"
    approved = web_client.post(form_action, form_payload, follow=False)
    assert approved.status_code in {302, 303}, approved.content
    returned = parse_qs(urlparse(approved["Location"]).query)
    assert returned.get("state") == ["dcr-state"]
    assert returned.get("code")
    return returned["code"][0]


def _exchange_code(
    web_client: Client,
    *,
    client_id: str,
    redirect_uri: str,
    code: str,
    verifier: str,
) -> str:
    response = web_client.post(
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
    assert response.status_code == 200, response.content
    body = _json(response)
    assert body["token_type"].lower() == "bearer"
    assert body["scope"] == "applications:read"
    assert body["access_token"]
    return body["access_token"]


def _create_public_application(web_access: str, prefix: str) -> int:
    api_client = Client()
    headers = {"HTTP_AUTHORIZATION": f"Bearer {web_access}"}
    company = api_client.post(
        COMPANIES_URL,
        {
            "company_name": f"MCP DCR {prefix} 公司",
            "recruitment_url": None,
        },
        content_type="application/json",
        **headers,
    )
    assert company.status_code == 201, company.content
    company_id = _json(company)["id"]
    application = api_client.post(
        APPLICATIONS_URL,
        {
            "company_id": company_id,
            "positions": [
                {
                    "position_name": f"{prefix} 后端开发",
                    "application_status": "applied",
                    "application_time": None,
                    "notes": f"{prefix} public fixture",
                    "interviews": [],
                }
            ],
            "shared_stages": [],
        },
        content_type="application/json",
        **headers,
    )
    assert application.status_code == 201, application.content
    return _json(application)["id"]


@pytest.fixture
def dcr_oauth_users() -> list[dict[str, str | int]]:
    users = []
    for prefix in ("mcp-dcr-a", "mcp-dcr-b"):
        web_client, credentials, web_access = _register_web_user(prefix)
        redirect_uri = f"https://{prefix}.example.test/callback"
        client_id = _register_dcr_client(web_client, redirect_uri)
        verifier, challenge = _pkce_pair(prefix)
        code = _authorize_with_public_login(
            web_client,
            client_id=client_id,
            redirect_uri=redirect_uri,
            verifier=verifier,
            challenge=challenge,
            credentials=credentials,
        )
        mcp_access = _exchange_code(
            web_client,
            client_id=client_id,
            redirect_uri=redirect_uri,
            code=code,
            verifier=verifier,
        )
        application_id = _create_public_application(web_access, prefix)
        users.append(
            {
                "client": web_client,
                "credentials": credentials,
                "web_access": web_access,
                "mcp_access": mcp_access,
                "application_id": application_id,
            }
        )
    return users


def test_protected_resource_metadata_is_public_and_points_to_mcp(client):
    response = client.get(PROTECTED_RESOURCE_METADATA_URL)

    assert response.status_code == 200, response.content
    body = _json(response)
    assert body["resource"] == MCP_RESOURCE
    assert body["authorization_servers"] == [MCP_ISSUER]
    assert "applications:read" in body["scopes_supported"]
    assert body["bearer_methods_supported"] == ["header"]


def test_authorization_server_metadata_advertises_cimd_and_pkce(client):
    response = client.get(AUTHORIZATION_SERVER_METADATA_URL)

    assert response.status_code == 200, response.content
    body = _json(response)
    assert body["issuer"] == MCP_ISSUER
    assert body["authorization_endpoint"].endswith(AUTHORIZE_URL)
    assert body["token_endpoint"].endswith(TOKEN_URL)
    assert "code" in body["response_types_supported"]
    assert "authorization_code" in body["grant_types_supported"]
    assert "none" in body["token_endpoint_auth_methods_supported"]
    assert "S256" in body["code_challenge_methods_supported"]
    assert "applications:read" in body["scopes_supported"]
    assert body["client_id_metadata_document_supported"] is True


def test_unauthenticated_modern_mcp_request_returns_resource_metadata_challenge(client):
    response = _mcp_request(client, "server/discover")

    assert response.status_code == 401, response.content
    challenge = response.get("WWW-Authenticate", "")
    assert "Bearer" in challenge
    assert "resource_metadata=" in challenge
    assert PROTECTED_RESOURCE_METADATA_URL in challenge
    assert b"server/discover" not in response.content


@pytest.mark.parametrize(
    "authorization",
    [
        "Bearer not-a-jwt",
        "Bearer eyJhbGciOiJub25lIn0.eyJzdWIiOiJvdGhlciJ9.",
        "Basic not-a-bearer-token",
    ],
)
def test_invalid_or_wrong_scheme_mcp_credentials_are_rejected_before_jsonrpc(
    client, authorization
):
    response = client.post(
        MCP_URL,
        {
            "jsonrpc": "2.0",
            "id": "invalid-auth",
            "method": "tools/list",
        },
        content_type="application/json",
        HTTP_AUTHORIZATION=authorization,
        HTTP_ACCEPT="application/json, text/event-stream",
        HTTP_ORIGIN="https://client.example.test",
    )

    assert response.status_code == 401, response.content
    assert b"tools/list" not in response.content


@pytest.mark.django_db
def test_existing_web_jwt_is_not_accepted_as_an_mcp_resource_token(client):
    username = f"mcp-web-jwt-{uuid.uuid4().hex[:12]}"
    credentials = {
        "username": username,
        "email": f"{username}@example.test",
        "password": PASSWORD,
    }
    registered = client.post(
        REGISTER_URL,
        {**credentials, "password_confirm": PASSWORD},
        content_type="application/json",
    )
    assert registered.status_code == 201, registered.content
    logged_in = client.post(LOGIN_URL, credentials, content_type="application/json")
    assert logged_in.status_code == 200, logged_in.content
    web_access = logged_in.json()["access"]

    response = _mcp_request(client, "server/discover", token=web_access)

    assert response.status_code == 401, response.content
    challenge = response.get("WWW-Authenticate", "")
    assert "resource_metadata=" in challenge


@pytest.mark.parametrize(
    "overrides",
    [
        {"code_challenge": None, "code_challenge_method": None},
        {"code_challenge_method": "plain"},
        {"redirect_uri": "https://client.example.test/other"},
        {"resource": "https://testserver/other"},
        {"scope": "applications:read applications:write"},
    ],
)
def test_authorize_rejects_unsafe_or_invalid_pkce_request(client, overrides):
    query = _oauth_authorize_query(**overrides)
    response = client.get(f"{AUTHORIZE_URL}?{query}")

    assert 400 <= response.status_code < 500, response.content
    if response["Content-Type"].startswith("application/json"):
        body = _json(response)
        assert body.get("error") or body.get("code")
    assert "access_token" not in response.content.decode(errors="replace")


@pytest.mark.parametrize(
    "payload",
    [
        {
            "grant_type": "authorization_code",
            "code": "not-a-code",
            "client_id": CLIENT_METADATA_URL,
            "redirect_uri": REDIRECT_URI,
            "code_verifier": "verifier-123",
            "resource": MCP_RESOURCE,
        },
        {
            "grant_type": "authorization_code",
            "code": "not-a-code",
            "client_id": CLIENT_METADATA_URL,
            "redirect_uri": REDIRECT_URI,
            "code_verifier": "verifier-123",
            "resource": "https://testserver/other",
        },
    ],
)
def test_token_endpoint_rejects_unknown_code_or_wrong_resource(client, payload):
    response = client.post(TOKEN_URL, payload, content_type="application/x-www-form-urlencoded")

    assert 400 <= response.status_code < 500, response.content
    body = _json(response)
    assert body.get("error") in {
        "invalid_request",
        "invalid_grant",
        "invalid_client",
        "invalid_target",
    }
    assert "access_token" not in response.content.decode(errors="replace")


def test_modern_server_discover_tools_list_and_find_are_available_without_initialize(
    client, dcr_oauth_users
):
    token = dcr_oauth_users[0]["mcp_access"]

    discover = _mcp_request(client, "server/discover", token=token)
    assert discover.status_code == 200, discover.content
    discover_body = _json(discover)
    assert discover_body.get("result", {}).get("protocolVersion") == "2026-07-28"

    tools = _mcp_request(client, "tools/list", token=token)
    assert tools.status_code == 200, tools.content
    tools_body = _json(tools)
    tool_list = tools_body["result"]["tools"]
    assert [tool["name"] for tool in tool_list] == ["find_applications"]
    find_tool = tool_list[0]
    assert find_tool["annotations"]["readOnlyHint"] is True
    properties = find_tool["inputSchema"]["properties"]
    assert {"application_id", "company_name", "position_name", "search"} <= set(
        properties
    )
    assert {"page", "page_size"} <= set(properties)
    assert "user_id" not in properties


def test_find_applications_returns_app012_shape_and_rejects_user_override(
    client, dcr_oauth_users
):
    token = dcr_oauth_users[0]["mcp_access"]

    response = _mcp_request(
        client,
        "tools/call",
        {
            "name": "find_applications",
            "arguments": {"page": 1, "page_size": 20},
        },
        token=token,
    )
    assert response.status_code == 200, response.content
    body = _json(response)["result"]
    assert body["isError"] is not True
    assert body["content"]
    assert body["structuredContent"]["count"] >= 0
    assert body["structuredContent"]["results"]
    item = body["structuredContent"]["results"][0] if body["structuredContent"]["results"] else None
    if item is not None:
        assert {"id", "company_id", "company", "company_name", "positions"} <= set(item)
        assert "user_id" not in item
        assert "notes" not in item["company"]

    override = _mcp_request(
        client,
        "tools/call",
        {
            "name": "find_applications",
            "arguments": {"user_id": 999999, "page": 1, "page_size": 20},
        },
        token=token,
    )
    assert override.status_code == 200, override.content
    override_body = _json(override)["result"]
    assert override_body.get("isError") is True or "error" in override_body
    assert "999999" not in override.content.decode(errors="replace")


def test_find_applications_isolation_does_not_return_another_users_application(
    client, dcr_oauth_users
):
    token_a = dcr_oauth_users[0]["mcp_access"]
    token_b = dcr_oauth_users[1]["mcp_access"]
    foreign_application_id = str(dcr_oauth_users[0]["application_id"])

    response = _mcp_request(
        client,
        "tools/call",
        {
            "name": "find_applications",
            "arguments": {"application_id": int(foreign_application_id)},
        },
        token=token_b,
    )
    assert response.status_code == 200, response.content
    result = _json(response)["result"]
    assert result.get("isError") is not True
    assert result["structuredContent"]["results"] == []

    owner_response = _mcp_request(
        client,
        "tools/call",
        {
            "name": "find_applications",
            "arguments": {"application_id": int(foreign_application_id)},
        },
        token=token_a,
    )
    assert owner_response.status_code == 200, owner_response.content
    owner_result = _json(owner_response)["result"]
    assert owner_result["structuredContent"]["count"] >= 1


def test_tools_list_and_find_do_not_require_protocol_session_header(
    client, dcr_oauth_users
):
    token = dcr_oauth_users[0]["mcp_access"]

    for method, params in (
        ("tools/list", None),
        (
            "tools/call",
            {"name": "find_applications", "arguments": {"page": 1, "page_size": 10}},
        ),
    ):
        response = _mcp_request(client, method, params, token=token)
        assert response.status_code == 200, response.content
        assert "Mcp-Session-Id" not in response


def test_unknown_tool_and_unknown_method_are_jsonrpc_errors(client, dcr_oauth_users):
    token = dcr_oauth_users[0]["mcp_access"]

    unknown_tool = _mcp_request(
        client,
        "tools/call",
        {"name": "create_application", "arguments": {}},
        token=token,
    )
    assert unknown_tool.status_code == 200, unknown_tool.content
    assert _json(unknown_tool)["result"].get("isError") is True

    unknown_method = _mcp_request(client, "not-a-real-method", token=token)
    assert unknown_method.status_code == 200, unknown_method.content
    assert "error" in _json(unknown_method)


def test_declared_2025_11_25_handshake_compatibility(client, dcr_oauth_users):
    token = dcr_oauth_users[0]["mcp_access"]
    initialized = _mcp_request(
        client,
        "initialize",
        {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "mcp-001-test-client", "version": "1.0"},
        },
        token=token,
    )
    assert initialized.status_code == 200, initialized.content
    initialize_result = _json(initialized)["result"]
    assert initialize_result["protocolVersion"] == "2025-11-25"
    session_id = initialized.get("Mcp-Session-Id")

    notification = _mcp_request(
        client,
        "notifications/initialized",
        token=token,
        session_id=session_id,
    )
    assert notification.status_code in {200, 202}, notification.content

    tools = _mcp_request(
        client,
        "tools/list",
        token=token,
        session_id=session_id,
    )
    assert tools.status_code == 200, tools.content
    assert [tool["name"] for tool in _json(tools)["result"]["tools"]] == [
        "find_applications"
    ]

