"""SHARE-001 black-box HTTP contract; no sharing models/source imports."""

from __future__ import annotations

import os
import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest
from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.test import Client, override_settings

BASE = "/api/v1/sharing/"
APPS = "/api/v1/applications/"
PASSWORD = "StrongPass_123"
AVATARS = {f"avatar-{index:02d}" for index in range(1, 9)}
PUBLIC_FIELDS = {"id", "username", "avatar", "relationship"}
PAGE_FIELDS = {"count", "page", "page_size", "total_pages", "next", "previous", "results"}
STAGES = ("ai_interview", "written_test", "first_interview", "second_interview", "third_interview", "hr_interview")
pytestmark = pytest.mark.django_db


def call(actor, method, path, data=None):
    kwargs = {"HTTP_AUTHORIZATION": f"Bearer {actor['access']}"} if actor else {}
    if method in {"post", "patch", "put"}:
        kwargs.update(data=data or {}, content_type="application/json")
    return getattr(Client(), method)(path, **kwargs)


def success(response, status=200):
    assert response.status_code == status, f"expected {status}, received {response.status_code}"
    assert response["Content-Type"].startswith("application/json")
    return response.json()


def error(response, status, code=None):
    body = success(response, status)
    assert {"code", "message", "details"} <= set(body)
    if code:
        assert body["code"] == code


def actor(prefix="share", *, legacy=False):
    name = f"{prefix}{uuid.uuid4().hex[:12]}"
    credentials = {"username": name, "email": f"{name}@example.com", "password": PASSWORD}
    if legacy:
        # Existing user fixture through Django's documented auth User API.
        user = get_user_model().objects.create_user(**credentials)
    else:
        body = success(call(None, "post", "/api/v1/auth/register/", {**credentials, "password_confirm": PASSWORD}), 201)
        assert set(body) == {"id", "username", "email", "date_joined"}
        user = get_user_model().objects.get(pk=body["id"])
    tokens = success(call(None, "post", "/api/v1/auth/login/", credentials))
    return {"id": user.pk, "username": name, "access": tokens["access"], "user": user}


@pytest.fixture
def people():
    return actor("alice"), actor("bob"), actor("carol")


def public(user, expected=None):
    assert set(user) == PUBLIC_FIELDS
    assert user["avatar"] in AVATARS
    assert user["relationship"] in {"none", "outgoing_pending", "incoming_pending", "connected"}
    if expected:
        assert user["id"] == expected["id"]
        assert user["username"] == expected["username"]


def request(sender, recipient, **extras):
    result = success(call(sender, "post", BASE + "requests/", {"recipient_id": recipient["id"], **extras}), 201)
    assert set(result) == {"id", "sender", "recipient", "status", "created_at", "responded_at"}
    public(result["sender"], sender)
    public(result["recipient"], recipient)
    assert result["status"] == "pending"
    assert result["responded_at"] is None
    return result


def respond(recipient, item, decision):
    result = success(call(recipient, "post", f"{BASE}requests/{item['id']}/respond/", {"decision": decision}))
    assert result["status"] == decision
    assert result["responded_at"] is not None
    return result


def connect(first, second):
    item = request(first, second)
    respond(second, item, "accepted")
    return item


def records(viewer, owner, query=""):
    return call(viewer, "get", f"{BASE}users/{owner['id']}/applications/{query}")


def application(owner, company="共享科技", position="后端工程师"):
    payload = {"company_name": company, "position_name": position, "notes": "PRIVATE_NOTE_9381", "application_url": "https://example.com/jobs/42"}
    for index, stage in enumerate(STAGES):
        payload[f"{stage}_time"] = f"2026-10-05T{9 + index:02d}:00:00+08:00"
        payload[f"{stage}_duration_minutes"] = 30 + index
    return success(call(owner, "post", APPS, payload), 201)


@pytest.mark.parametrize(("method", "path", "data"), [
    ("get", "me/", None), ("get", "users/recommendations/", None),
    ("get", "users/1/", None), ("get", "requests/", None),
    ("post", "requests/", {"recipient_id": 1}),
    ("post", "requests/1/respond/", {"decision": "accepted"}),
    ("get", "connections/", None), ("delete", "connections/1/", None),
    ("get", "users/1/applications/", None),
])
def test_all_new_endpoints_require_authentication(method, path, data):
    error(call(None, method, BASE + path, data), 401)


def test_new_and_legacy_user_avatars_are_safe_stable_and_consistent(people):
    first, second, _ = people
    old = actor("legacy", legacy=True)
    for person in (first, second, old):
        me = success(call(person, "get", BASE + "me/"))
        public(me, person)
        assert me == success(call(person, "get", BASE + "me/"))
        viewer = second if person == first else first
        found = success(call(viewer, "get", f"{BASE}users/{person['id']}/"))
        public(found, person)
        assert found["avatar"] == me["avatar"]
    item = request(first, old)
    assert item["recipient"]["avatar"] == success(call(old, "get", BASE + "me/"))["avatar"]


@pytest.mark.parametrize("count", [None, 1, 3, 50])
def test_recommendation_count_and_exclusion_rules(people, count):
    first, second, third = people
    request(first, second)
    connect(third, first)
    for index in range(12):
        get_user_model().objects.create_user(username=f"rec{index}{uuid.uuid4().hex[:8]}")
    disabled = get_user_model().objects.create_user(username="disabled", is_active=False)
    config = {} if count is None else {"SHARING_RECOMMENDATION_COUNT": count}
    with override_settings(**config):
        body = success(call(first, "get", BASE + "users/recommendations/"))
    assert set(body) == {"count", "results"}
    ids = [person["id"] for person in body["results"]]
    assert body["count"] == len(ids) == min(count or 10, 12)
    assert len(ids) == len(set(ids))
    assert not {first["id"], second["id"], third["id"], disabled.pk}.intersection(ids)
    for person in body["results"]:
        public(person)
        assert person["relationship"] == "none"


def test_recommendations_with_no_available_users_returns_empty(people):
    first, second, third = people
    request(second, first)
    connect(first, third)
    assert success(call(first, "get", BASE + "users/recommendations/")) == {"count": 0, "results": []}


@pytest.mark.parametrize("value", ["0", "51", "abc", "10.5", "-1"])
def test_invalid_recommendation_environment_is_rejected_by_startup_check(value):
    environment = os.environ.copy()
    environment["SHARING_RECOMMENDATION_COUNT"] = value
    result = subprocess.run(["uv", "run", "--no-sync", "python", "manage.py", "check"], cwd=Path(__file__).resolve().parents[1], env=environment, capture_output=True, text=True, timeout=45)
    assert result.returncode != 0, "invalid recommendation configuration must reject startup/check"
    assert "SHARING_RECOMMENDATION_COUNT" in result.stdout + result.stderr


def test_search_hides_self_missing_and_inactive_and_shows_pending_relationships(people):
    first, second, third = people
    public(success(call(first, "get", f"{BASE}users/{second['id']}/")), second)
    third["user"].is_active = False
    third["user"].save(update_fields=["is_active"])
    for target in (first["id"], third["id"], 99999999):
        error(call(first, "get", f"{BASE}users/{target}/"), 404, "NOT_FOUND")
    request(first, second)
    assert success(call(first, "get", f"{BASE}users/{second['id']}/"))["relationship"] == "outgoing_pending"
    assert success(call(second, "get", f"{BASE}users/{first['id']}/"))["relationship"] == "incoming_pending"


@pytest.mark.parametrize("target", ["0", "-1", "abc", "1.5"])
def test_invalid_search_id_is_structured_validation_error(people, target):
    error(call(people[0], "get", f"{BASE}users/{target}/"), 400, "VALIDATION_ERROR")


@pytest.mark.parametrize("target", [None, 0, -1, "abc", 1.5, True])
def test_invalid_recipient_cannot_create_request(people, target):
    error(call(people[0], "post", BASE + "requests/", {"recipient_id": target}), 400, "VALIDATION_ERROR")


def test_self_inactive_and_missing_recipient_and_forged_fields_do_not_grant_access(people):
    first, second, third = people
    error(call(first, "post", BASE + "requests/", {"recipient_id": first["id"]}), 400, "VALIDATION_ERROR")
    third["user"].is_active = False
    third["user"].save(update_fields=["is_active"])
    for target in (third["id"], 99999999):
        error(call(first, "post", BASE + "requests/", {"recipient_id": target}), 404, "NOT_FOUND")
    response = call(first, "post", BASE + "requests/", {"recipient_id": second["id"], "sender": second["id"], "owner": second["id"], "status": "accepted"})
    assert response.status_code in {201, 400}
    if response.status_code == 201:
        body = success(response, 201)
        assert body["sender"]["id"] == first["id"]
        assert body["status"] == "pending"
    error(records(first, second), 404, "NOT_FOUND")


def test_pending_requests_are_private_do_not_authorize_and_reverse_request_conflicts(people):
    first, second, third = people
    item = request(first, second)
    first_history = success(call(first, "get", BASE + "requests/"))
    second_history = success(call(second, "get", BASE + "requests/"))
    assert [row["id"] for row in first_history["outgoing"]] == [item["id"]]
    assert first_history["incoming"] == []
    assert [row["id"] for row in second_history["incoming"]] == [item["id"]]
    assert success(call(third, "get", BASE + "requests/")) == {"incoming": [], "outgoing": []}
    for viewer, owner in ((first, second), (second, first), (third, first), (first, first)):
        error(records(viewer, owner), 404, "NOT_FOUND")
    for sender, recipient in ((first, second), (second, first)):
        error(call(sender, "post", BASE + "requests/", {"recipient_id": recipient["id"]}), 409, "SHARING_CONFLICT")
    for intruder in (first, third):
        error(call(intruder, "post", f"{BASE}requests/{item['id']}/respond/", {"decision": "accepted"}), 404, "NOT_FOUND")
    error(call(second, "post", f"{BASE}requests/{item['id']}/respond/", {"decision": "automatic"}), 400, "VALIDATION_ERROR")
    assert success(call(first, "get", BASE + "connections/")) == {"results": []}


def test_rejection_is_not_authorization_and_reapplication_preserves_history(people):
    first, second, _ = people
    old = request(first, second)
    respond(second, old, "rejected")
    error(records(first, second), 404, "NOT_FOUND")
    error(records(second, first), 404, "NOT_FOUND")
    error(call(second, "post", f"{BASE}requests/{old['id']}/respond/", {"decision": "accepted"}), 409, "SHARING_CONFLICT")
    newer = request(first, second)
    history = success(call(first, "get", BASE + "requests/"))["outgoing"]
    assert [row["id"] for row in history] == [newer["id"], old["id"]]
    assert [row["status"] for row in history] == ["pending", "rejected"]


def test_acceptance_grants_bidirectional_read_only_safe_records_without_legacy_access(people):
    first, second, third = people
    own = application(first, "Alice公司")
    other = application(second, "Bob公司")
    item = connect(first, second)
    for viewer, owner, expected in ((first, second, other), (second, first, own)):
        connections = success(call(viewer, "get", BASE + "connections/"))["results"]
        assert len(connections) == 1
        assert connections[0]["id"] == item["id"]
        public(connections[0]["user"], owner)
        assert connections[0]["user"]["relationship"] == "connected"
        body = success(records(viewer, owner))
        assert PAGE_FIELDS <= set(body)
        assert body["count"] == 1
        shared = body["results"][0]
        assert set(shared) == set(expected) - {"notes", "user"}
        assert shared == {key: value for key, value in expected.items() if key not in {"notes", "user"}}
        assert "PRIVATE_NOTE_9381" not in str(body)
        for method in ("get", "patch", "delete"):
            error(call(viewer, method, f"{APPS}{expected['id']}/", {"notes": "attack"}), 404, "NOT_FOUND")
        for method in ("post", "put", "patch", "delete"):
            denied = call(viewer, method, f"{BASE}users/{owner['id']}/applications/", {"company_name": "attack"})
            assert denied.status_code in {403, 404, 405}
        mine = success(call(viewer, "get", APPS + f"?user={owner['id']}"))
        assert expected["id"] not in [row["id"] for row in mine["results"]]
        error(call(viewer, "post", BASE + "requests/", {"recipient_id": owner["id"]}), 409, "SHARING_CONFLICT")
    error(records(third, first), 404, "NOT_FOUND")
    error(records(third, second), 404, "NOT_FOUND")
    assert success(call(third, "get", BASE + "connections/")) == {"results": []}
    error(call(third, "delete", f"{BASE}connections/{item['id']}/"), 404, "NOT_FOUND")
    assert success(call(second, "get", f"{APPS}{other['id']}/")) == other


@pytest.mark.parametrize("revoker_index", [0, 1])
def test_either_party_can_immediately_revoke_both_directions_without_consent(people, revoker_index):
    first, second, _ = people
    application(first)
    application(second)
    item = connect(first, second)
    assert success(records(first, second))["count"] == 1
    assert success(records(second, first))["count"] == 1
    assert call(people[revoker_index], "delete", f"{BASE}connections/{item['id']}/").status_code == 204
    for viewer, owner in ((first, second), (second, first)):
        error(records(viewer, owner), 404, "NOT_FOUND")
        assert success(call(viewer, "get", BASE + "connections/")) == {"results": []}
        assert success(call(viewer, "get", f"{BASE}users/{owner['id']}/"))["relationship"] == "none"
    assert success(call(first, "get", BASE + "requests/"))["outgoing"][0]["status"] == "revoked"
    error(call(second, "delete", f"{BASE}connections/{item['id']}/"), 404, "NOT_FOUND")
    newer = request(second, first)
    assert newer["id"] != item["id"]
    error(records(first, second), 404, "NOT_FOUND")


def test_deactivated_connected_user_is_hidden_and_unreadable(people):
    first, second, _ = people
    connect(first, second)
    second["user"].is_active = False
    second["user"].save(update_fields=["is_active"])
    error(records(first, second), 404, "NOT_FOUND")
    assert success(call(first, "get", BASE + "connections/")) == {"results": []}
    error(call(first, "get", f"{BASE}users/{second['id']}/"), 404, "NOT_FOUND")


def test_shared_pagination_search_and_stable_order_are_owner_scoped(people):
    first, second, third = people
    expected = [application(second, f"共享公司{index:02d}", "算法岗" if index == 0 else "后端岗") for index in range(21)]
    application(first, "共享公司自己")
    application(third, "共享公司第三方")
    connect(first, second)
    body = success(records(first, second))
    assert body["page"] == 1 and body["page_size"] == 20
    assert body["count"] == 21 and body["total_pages"] == 2
    assert [row["id"] for row in body["results"]] == [row["id"] for row in reversed(expected)][0:20]
    for size in (10, 20, 50, 100):
        body = success(records(first, second, f"?page_size={size}"))
        assert body["page_size"] == size and len(body["results"]) == min(size, 21)
    second_page = success(records(first, second, "?page=2&page_size=10"))
    assert second_page["count"] == 21 and len(second_page["results"]) == 10
    assert second_page["next"] and second_page["previous"]
    for query in ("算法", "共享公司00"):
        found = success(records(first, second, f"?search={query}"))
        assert [row["id"] for row in found["results"]] == [expected[0]["id"]]
    empty = success(records(first, second, "?page=99"))
    assert empty["count"] == 21 and empty["results"] == []
    assert success(records(first, second, "?search=missing"))["count"] == 0
    for query in ("page=0", "page=-1", "page=abc", "page_size=1", "page_size=101", "page_size=20.5"):
        error(records(first, second, f"?{query}"), 400, "VALIDATION_ERROR")


def test_history_keeps_only_recent_100_without_overwriting_rejected_requests(people):
    first, second, _ = people
    ids = []
    for _ in range(101):
        item = request(first, second)
        ids.append(item["id"])
        respond(second, item, "rejected")
    outgoing = success(call(first, "get", BASE + "requests/"))["outgoing"]
    incoming = success(call(second, "get", BASE + "requests/"))["incoming"]
    assert [item["id"] for item in outgoing] == ids[-100:][::-1]
    assert [item["id"] for item in incoming] == ids[-100:][::-1]
    assert all(item["status"] == "rejected" for item in outgoing + incoming)


@pytest.mark.django_db(transaction=True)
def test_concurrent_opposite_requests_create_only_one_pending_pair(people):
    first, second, _ = people
    gate = Barrier(2)

    def send(sender, recipient):
        close_old_connections()
        try:
            gate.wait(timeout=10)
            return call(sender, "post", BASE + "requests/", {"recipient_id": recipient["id"]}).status_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(send, first, second), pool.submit(send, second, first)]
        statuses = [future.result(timeout=30) for future in futures]
    assert sorted(statuses) == [201, 409]
    history = success(call(first, "get", BASE + "requests/"))
    assert len(history["incoming"]) + len(history["outgoing"]) == 1
    assert success(call(first, "get", BASE + "connections/")) == {"results": []}
    error(records(first, second), 404, "NOT_FOUND")

