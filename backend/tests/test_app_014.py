"""APP-012 black-box tests for the authenticated prompt-management API."""

from __future__ import annotations

import uuid

import pytest
from django.test import Client

REGISTER_URL = "/api/v1/auth/register/"
LOGIN_URL = "/api/v1/auth/login/"
PROMPTS_URL = "/api/v1/prompts/"
PASSWORD = "StrongPass_123"


@pytest.fixture
def client():
    return Client()


def _register_and_login(client: Client, prefix: str) -> dict[str, str | int]:
    username = f"{prefix}-{uuid.uuid4().hex[:12]}"
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
    login = client.post(LOGIN_URL, credentials, content_type="application/json")
    assert login.status_code == 200, login.content
    return {"id": registered.json()["id"], "access": login.json()["access"]}


def _headers(session: dict[str, str | int]) -> dict[str, str]:
    return {"HTTP_AUTHORIZATION": f"Bearer {session['access']}"}


def _json(response):
    assert response["Content-Type"].startswith("application/json")
    return response.json()


def _create(client, session, title="我的提示词", content="请介绍一个项目"):
    return client.post(
        PROMPTS_URL,
        {"title": title, "content": content},
        content_type="application/json",
        **_headers(session),
    )


@pytest.mark.django_db
def test_first_list_initializes_presets_once_and_isolated_between_users(client):
    user_a = _register_and_login(client, "app012-prompt-a")
    user_b = _register_and_login(client, "app012-prompt-b")

    assert client.get(PROMPTS_URL).status_code == 401
    first = client.get(PROMPTS_URL, **_headers(user_a))
    assert first.status_code == 200, first.content
    body = _json(first)
    assert set(body) == {"count", "page", "page_size", "total_pages", "next", "previous", "results"}
    assert body["results"]
    assert {"id", "title", "content", "is_preset", "created_at", "updated_at"}.issubset(body["results"][0])
    titles = " ".join(item["title"] for item in body["results"])
    assert all(term in titles for term in ("自我介绍", "项目经历深挖", "行为面试 STAR"))
    assert all(item["is_preset"] is True for item in body["results"])

    second = client.get(PROMPTS_URL, **_headers(user_a))
    assert second.status_code == 200
    assert [item["id"] for item in _json(second)["results"]] == [item["id"] for item in body["results"]]

    other = client.get(PROMPTS_URL, **_headers(user_b))
    assert other.status_code == 200
    assert {item["title"] for item in _json(other)["results"]} == {item["title"] for item in body["results"]}
    created = _create(client, user_a, "仅 A 可见", "私有正文")
    assert created.status_code == 201, created.content
    b_titles = {item["title"] for item in _json(client.get(PROMPTS_URL, **_headers(user_b))["results"])}
    assert "仅 A 可见" not in b_titles


@pytest.mark.django_db
def test_search_matches_title_or_content_case_insensitively_and_returns_pagination(client):
    session = _register_and_login(client, "app012-prompt-search")
    assert _create(client, session, "System Design", "Explain caching strategy").status_code == 201
    assert _create(client, session, "面试复盘", "KAFKA consumer lag").status_code == 201

    by_title = client.get(f"{PROMPTS_URL}?search=system%20design&page_size=1", **_headers(session))
    assert by_title.status_code == 200, by_title.content
    title_body = _json(by_title)
    assert title_body["count"] == 1
    assert title_body["results"][0]["title"] == "System Design"
    assert title_body["page_size"] == 1
    assert title_body["total_pages"] == 1

    by_content = client.get(f"{PROMPTS_URL}?search=kAfKa", **_headers(session))
    assert by_content.status_code == 200
    assert [item["title"] for item in _json(by_content)["results"]] == ["面试复盘"]


@pytest.mark.django_db
def test_create_patch_delete_and_validation_are_owner_bound(client):
    owner = _register_and_login(client, "app012-prompt-crud")
    other = _register_and_login(client, "app012-prompt-other")
    created = _create(client, owner, "  自定义标题  ", "  自定义内容  ")
    assert created.status_code == 201, created.content
    body = _json(created)
    prompt_id = body["id"]
    assert body["title"] == "自定义标题"
    assert body["content"] == "自定义内容"
    assert body["is_preset"] is False
    assert "user" not in body and "owner" not in body

    patched = client.patch(
        f"{PROMPTS_URL}{prompt_id}/",
        {"title": "更新标题", "content": "更新正文"},
        content_type="application/json",
        **_headers(owner),
    )
    assert patched.status_code == 200, patched.content
    assert _json(patched)["title"] == "更新标题"
    assert _json(client.get(f"{PROMPTS_URL}{prompt_id}/", **_headers(owner)))["content"] == "更新正文"

    for method in ("get", "patch", "delete"):
        response = getattr(client, method)(
            f"{PROMPTS_URL}{prompt_id}/",
            {"title": "越权", "content": "越权"} if method == "patch" else None,
            content_type="application/json" if method == "patch" else None,
            **_headers(other),
        )
        assert response.status_code == 404, response.content

    deleted = client.delete(f"{PROMPTS_URL}{prompt_id}/", **_headers(owner))
    assert deleted.status_code == 204
    assert client.get(f"{PROMPTS_URL}{prompt_id}/", **_headers(owner)).status_code == 404

    for payload in (
        {"title": "", "content": "正文"},
        {"title": "标题", "content": "   "},
        {"title": "x" * 101, "content": "正文"},
        {"title": "标题", "content": "x" * 10001},
    ):
        invalid = _create(client, owner, **payload)
        assert invalid.status_code == 400, invalid.content
        assert invalid.json().get("code") in {"VALIDATION_ERROR", None}


def _prompt_id(client, session, title, content):
    response = _create(client, session, title, content)
    assert response.status_code == 201, response.content
    return _json(response)["id"]


@pytest.mark.django_db
def test_preset_can_be_updated_and_deleted_without_reappearing(client):
    session = _register_and_login(client, "app012-prompt-preset")
    initial = _json(client.get(PROMPTS_URL, **_headers(session)))
    preset = next(item for item in initial["results"] if item["title"] == "自我介绍")
    updated = client.patch(
        f"{PROMPTS_URL}{preset['id']}/",
        {"content": "我自己的自我介绍"},
        content_type="application/json",
        **_headers(session),
    )
    assert updated.status_code == 200, updated.content
    assert _json(updated)["is_preset"] is True
    assert client.delete(f"{PROMPTS_URL}{preset['id']}/", **_headers(session)).status_code == 204
    refreshed = _json(client.get(PROMPTS_URL, **_headers(session)))
    assert preset["id"] not in {item["id"] for item in refreshed["results"]}
    assert "自我介绍" not in {item["title"] for item in refreshed["results"]}


@pytest.mark.django_db
def test_client_cannot_assign_owner_and_invalid_ids_do_not_leak(client):
    owner = _register_and_login(client, "app012-prompt-owner")
    other = _register_and_login(client, "app012-prompt-attacker")
    created = client.post(
        PROMPTS_URL,
        {"title": "安全提示", "content": "正文", "user": other["id"], "owner": other["id"]},
        content_type="application/json",
        **_headers(owner),
    )
    assert created.status_code == 201, created.content
    result = _json(created)
    assert result["title"] == "安全提示"
    listed = _json(client.get(PROMPTS_URL, **_headers(other)))
    assert "安全提示" not in {item["title"] for item in listed["results"]}
    assert client.get(f"{PROMPTS_URL}99999999/", **_headers(owner)).status_code == 404
