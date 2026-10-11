"""Real HTTP/process black-box test for MCP-003 proposal persistence.

The test never imports Django, application models, URLs, or MCP internals.  It
starts uvicorn as an external process and uses only public HTTP endpoints.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import uuid
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

import pytest
import requests


MCP_RESOURCE = "https://testserver/mcp"
CLIENT_METADATA_URL = "https://real-http-client.example.test/mcp.json"
REDIRECT_URI = "https://real-http-client.example.test/callback"
PASSWORD = "StrongPass_123"


class _FormParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.action = ""
        self.inputs: dict[str, str] = {}

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "form" and not self.action:
            self.action = values.get("action", "")
        if tag == "input" and values.get("name"):
            self.inputs[values["name"]] = values.get("value", "")


def _json(response):
    assert response.headers.get("content-type", "").startswith("application/json"), response.text
    return response.json()


def _wait_for_server(base_url: str, process: subprocess.Popen, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if process.poll() is not None:
            raise AssertionError(f"uvicorn exited early with code {process.returncode}")
        try:
            response = requests.get(f"{base_url}/mcp", timeout=1)
            if response.status_code in {401, 403, 405}:
                return
        except requests.RequestException:
            pass
        time.sleep(0.2)
    raise AssertionError(f"uvicorn did not become reachable: {base_url}")


def _start_server(port: int, log_path: Path):
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    repository_root = Path(__file__).resolve().parents[2]
    env["PYTHONPATH"] = str(repository_root) + os.pathsep + env.get("PYTHONPATH", "")
    log = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        ["uv", "run", "--no-sync", "python", "-m", "uvicorn", "backend.config.asgi:application", "--host", "127.0.0.1", "--port", str(port)],
        # uv must run from the backend project, while PYTHONPATH makes the
        # documented ``backend.config.asgi:application`` import resolvable.
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    try:
        _wait_for_server(f"http://127.0.0.1:{port}", process)
    except Exception:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        log.close()
        raise
    return process, log


def _stop_server(process, log):
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
    log.close()
    return process.returncode


def _register_and_login(base_url: str):
    session = requests.Session()
    username = f"mcp-real-{uuid.uuid4().hex[:12]}"
    credentials = {"username": username, "email": f"{username}@example.test", "password": PASSWORD}
    registered = session.post(
        f"{base_url}/api/v1/auth/register/",
        json={**credentials, "password_confirm": PASSWORD},
        timeout=10,
    )
    assert registered.status_code == 201, registered.text

    oauth_login = session.get(f"{base_url}/oauth/login", timeout=10)
    assert oauth_login.status_code == 200, oauth_login.text
    parser = _FormParser()
    parser.feed(oauth_login.text)
    payload = dict(parser.inputs)
    payload.update({"username": username, "password": PASSWORD, "next": "/"})
    action = urljoin(base_url, parser.action or "/oauth/login")
    logged_in = session.post(action, data=payload, allow_redirects=False, timeout=10)
    assert logged_in.status_code in {200, 302, 303}, logged_in.text
    assert session.cookies.get("sessionid")
    return session


def _oauth_token(base_url: str, session: requests.Session):
    dcr = session.post(
        f"{base_url}/oauth/register",
        json={
            "client_name": "MCP-003 real restart test",
            "redirect_uris": [REDIRECT_URI],
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
        },
        timeout=10,
    )
    assert dcr.status_code in {200, 201}, dcr.text
    client_id = _json(dcr)["client_id"]
    verifier = f"real-restart-verifier-{uuid.uuid4().hex}"
    import base64
    import hashlib

    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "scope": "applications:read applications:write",
        "state": "real-restart-state",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "resource": MCP_RESOURCE,
    }
    query = urlencode(params)
    authorized = session.get(
        f"{base_url}/oauth/authorize?{query}",
        allow_redirects=False,
        timeout=10,
    )
    assert authorized.status_code in {200, 302, 303}, authorized.text
    if authorized.status_code in {302, 303}:
        returned = parse_qs(urlparse(authorized.headers["Location"]).query)
        assert returned.get("state") == ["real-restart-state"]
        code = returned["code"][0]
    else:
        parser = _FormParser()
        parser.feed(authorized.text)
        assert parser.action or parser.inputs
        consent = dict(parser.inputs)
        consent.update(params)
        consent["allow"] = "Authorize"
        action = urljoin(base_url, parser.action or "/oauth/authorize")
        if "?" not in action:
            action = f"{action}?{query}"
        approved = session.post(action, data=consent, allow_redirects=False, timeout=10)
        assert approved.status_code in {302, 303}, approved.text
        returned = parse_qs(urlparse(approved.headers["Location"]).query)
        assert returned.get("state") == ["real-restart-state"]
        code = returned["code"][0]
    token = session.post(
        f"{base_url}/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "code_verifier": verifier,
            "resource": MCP_RESOURCE,
        },
        timeout=10,
    )
    assert token.status_code == 200, token.text
    body = _json(token)
    assert "applications:write" in body["scope"]
    return body["access_token"]


def _mcp(base_url, token, method, params=None):
    response = requests.post(
        f"{base_url}/mcp",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, text/event-stream",
            "Origin": "https://client.example.test",
        },
        json={
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": method,
            **({"params": params} if params is not None else {}),
        },
        timeout=15,
    )
    assert response.status_code == 200, response.text
    return _json(response)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def test_preview_survives_real_service_restart_and_second_process(tmp_path):
    port_a, port_b, port_c = _free_port(), _free_port(), _free_port()
    base_a, base_b, base_c = (f"http://127.0.0.1:{port}" for port in (port_a, port_b, port_c))
    process_a = process_b = process_c = None
    logs = []
    lifecycle = []
    try:
        process_a, log_a = _start_server(port_a, tmp_path / "uvicorn-a.log")
        logs.append(log_a)
        lifecycle.append({"process": "A", "port": port_a, "pid": process_a.pid, "event": "started"})
        session = _register_and_login(base_a)
        token = _oauth_token(base_a, session)
        created = _mcp(
            base_a,
            token,
            "tools/call",
            {"name": "create_application", "arguments": {"company_name": "真实重启公司", "position_name": "后端", "application_status": "applied"}},
        )["result"]["structuredContent"]["application"]
        target = {"application_id": created["id"], "position_id": created["positions"][0]["id"]}
        proposal = _mcp(
            base_a,
            token,
            "tools/call",
            {
                "name": "preview_application_change",
                "arguments": {
                    "operation": "upsert_application_stage",
                    "target": target,
                    "change": {"stage_type": "interview", "interview_round": "second", "interview_name": "二面", "scheduled_at": "2026-11-10T14:00:00+08:00", "duration_minutes": 60},
                    "idempotency_key": "real-restart-preview",
                },
            },
        )["result"]["structuredContent"]
        proposal_id = proposal["proposal_id"]
        lifecycle.append({"process": "A", "port": port_a, "event": "preview", "proposal_id": proposal_id})
        return_code_a = _stop_server(process_a, log_a)
        lifecycle.append({"process": "A", "port": port_a, "event": "stopped", "returncode": return_code_a})
        process_a = None

        process_b, log_b = _start_server(port_b, tmp_path / "uvicorn-b.log")
        logs.append(log_b)
        lifecycle.append({"process": "B", "port": port_b, "pid": process_b.pid, "event": "started"})
        applied = _mcp(base_b, token, "tools/call", {"name": "apply_application_change", "arguments": {"proposal_id": proposal_id, "confirm": True, "idempotency_key": "real-restart-apply"}})["result"]["structuredContent"]
        assert applied["status"] == "applied"
        assert applied["proposal_id"] == proposal_id
        assert applied["audit_id"]
        lifecycle.append({"process": "B", "port": port_b, "event": "apply", "proposal_id": proposal_id, "audit_id": applied["audit_id"], "status": applied["status"]})

        process_c, log_c = _start_server(port_c, tmp_path / "uvicorn-c.log")
        logs.append(log_c)
        lifecycle.append({"process": "C", "port": port_c, "pid": process_c.pid, "event": "started_concurrent"})
        replay = _mcp(base_c, token, "tools/call", {"name": "apply_application_change", "arguments": {"proposal_id": proposal_id, "confirm": True, "idempotency_key": "real-restart-apply"}})["result"]["structuredContent"]
        assert replay["status"] == "applied"
        assert replay["idempotent_replay"] is True
        assert replay["audit_id"] == applied["audit_id"]
        result = _mcp(base_c, token, "tools/call", {"name": "find_applications", "arguments": {"application_id": created["id"]}})["result"]["structuredContent"]
        application = result["results"][0]
        interview = application["positions"][0]["interviews"][0]
        assert interview["name"] == "二面"
        assert interview["duration_minutes"] == 60
        lifecycle.append({"process": "C", "port": port_c, "event": "replay_and_read", "proposal_id": proposal_id, "audit_id": replay["audit_id"], "idempotent_replay": True})
        print(json.dumps({"lifecycle": lifecycle}, ensure_ascii=False))
    finally:
        for name, process, log, port in (("C", process_c, logs[-1] if process_c else None, port_c), ("B", process_b, logs[-2] if process_b and process_c else logs[-1] if process_b else None, port_b), ("A", process_a, logs[0] if process_a else None, port_a)):
            if process is not None:
                code = _stop_server(process, log)
                lifecycle.append({"process": name, "port": port, "event": "cleaned", "returncode": code})

