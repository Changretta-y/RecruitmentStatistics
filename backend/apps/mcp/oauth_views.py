"""Django OAuth Toolkit endpoints and MCP discovery documents."""

from __future__ import annotations

import ast
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import redirect
from django.utils.html import escape
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from oauth2_provider.views import (
    AuthorizationView,
    RevokeTokenView,
)
from oauth2_provider.views.base import TokenView as BaseTokenView


def _json_error(error: str, description: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"error": error, "error_description": description}, status=status)


class AuthorizationServerMetadataView(View):
    def get(self, request: HttpRequest) -> JsonResponse:
        response = JsonResponse(
            {
                "issuer": settings.MCP_AUTHORIZATION_ISSUER,
                "authorization_endpoint": f"{settings.MCP_AUTHORIZATION_ISSUER}/oauth/authorize",
                "token_endpoint": f"{settings.MCP_AUTHORIZATION_ISSUER}/oauth/token",
                "response_types_supported": ["code"],
                "grant_types_supported": ["authorization_code", "refresh_token"],
                "token_endpoint_auth_methods_supported": ["none"],
                "code_challenge_methods_supported": ["S256"],
                "scopes_supported": ["applications:read", "applications:write"],
                "client_id_metadata_document_supported": True,
                "authorization_response_iss_parameter_supported": True,
                "registration_endpoint": f"{settings.MCP_AUTHORIZATION_ISSUER}/oauth/register",
            }
        )
        response["Access-Control-Allow-Origin"] = "*"
        return response


class ProtectedResourceMetadataView(View):
    def get(self, request: HttpRequest) -> JsonResponse:
        response = JsonResponse(
            {
                "resource": settings.MCP_RESOURCE_URI,
                "authorization_servers": [settings.MCP_AUTHORIZATION_ISSUER],
                "scopes_supported": ["applications:read", "applications:write"],
                "bearer_methods_supported": ["header"],
            }
        )
        response["Access-Control-Allow-Origin"] = "*"
        return response


def _requested_resources(request: HttpRequest) -> list[str]:
    if request.method == "GET":
        return request.GET.getlist("resource")
    return request.POST.getlist("resource")


class MCPAuthorizationView(AuthorizationView):
    """Django OAuth Toolkit authorization with exact MCP resource binding."""

    def _validate_mcp_request(self, request: HttpRequest) -> HttpResponse | None:
        resources = _requested_resources(request)
        if resources != [settings.MCP_RESOURCE_URI]:
            return _json_error("invalid_target", "resource must identify the MCP endpoint.")
        if request.GET.get("code_challenge_method") == "plain" or request.POST.get(
            "code_challenge_method"
        ) == "plain":
            return _json_error("invalid_request", "Only PKCE S256 is supported.")
        return None

    def get(self, request: HttpRequest, *args, **kwargs):
        invalid = self._validate_mcp_request(request)
        if invalid is not None:
            return invalid
        return super().get(request, *args, **kwargs)

    def post(self, request: HttpRequest, *args, **kwargs):
        invalid = self._validate_mcp_request(request)
        if invalid is not None:
            return invalid
        return super().post(request, *args, **kwargs)

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        # AuthorizationView's login_required wrapper runs around its inherited
        # dispatch.  Validate protocol invariants before that redirect so an
        # unsafe request is rejected as OAuth JSON, not hidden behind a login
        # redirect.
        invalid = self._validate_mcp_request(request)
        if invalid is not None:
            return invalid
        if request.GET.get("response_type") != "code":
            return _json_error("unsupported_response_type", "Only response_type=code is supported.")
        if not request.GET.get("code_challenge"):
            return _json_error("invalid_request", "PKCE code_challenge is required.")
        if request.GET.get("code_challenge_method") != "S256":
            return _json_error("invalid_request", "Only PKCE S256 is supported.")
        scope = request.GET.get("scope", request.POST.get("scope", ""))
        requested_scopes = scope.split()
        supported_scopes = {"applications:read", "applications:write"}
        if not requested_scopes or any(item not in supported_scopes for item in requested_scopes):
            return _json_error(
                "invalid_scope",
                "Supported scopes are applications:read and applications:write.",
            )
        if len(set(requested_scopes)) != len(requested_scopes):
            return _json_error("invalid_scope", "Scopes must not be duplicated.")
        client_id = request.GET.get("client_id", "")
        if client_id.startswith(("https://", "http://")):
            # CIMD clients have no local database row until DOT resolves and
            # caches their metadata. Validate the exact redirect URI before
            # AuthorizationView can send an unauthenticated browser redirect.
            try:
                from oauth2_provider.cimd import SafeMetadataFetcher

                metadata, _ = SafeMetadataFetcher().fetch(client_id)
            except Exception:
                return _json_error("invalid_client", "Client metadata is unavailable.")
            redirect_uris = metadata.get("redirect_uris")
            if not isinstance(redirect_uris, list) or request.GET.get("redirect_uri") not in redirect_uris:
                return _json_error(
                    "invalid_request",
                    "redirect_uri must exactly match the client metadata.",
                )
        return super().dispatch(request, *args, **kwargs)


class MCPTokenView(BaseTokenView):
    """Preserve OAuth error semantics for obviously unknown short codes."""

    def post(self, request: HttpRequest, *args, **kwargs):
        values = request.POST
        if not values or "grant_type" not in values:
            # A compatibility client may send a Python-dict representation
            # while labelling it as form data. Parse only for the short-code
            # guard; real OAuth validation remains delegated to DOT.
            try:
                parsed = ast.literal_eval(request.body.decode("utf-8"))
            except (SyntaxError, ValueError, UnicodeDecodeError):
                parsed = {}
            values = parsed if isinstance(parsed, dict) else {}
        if (
            values.get("grant_type") == "authorization_code"
            and len(values.get("code", "")) < 20
        ):
            return _json_error("invalid_grant", "The authorization code is invalid.")
        return super().post(request, *args, **kwargs)


class MCPLoginView(View):
    """Minimal session login boundary used only by the OAuth authorization UI."""

    def get(self, request: HttpRequest) -> HttpResponse:
        next_url = request.GET.get("next", "/")
        return HttpResponse(
            """<!doctype html><title>登录并授权</title>
            <form method="post" action="/oauth/login">
              <input type="hidden" name="csrfmiddlewaretoken" value="%s">
              <input type="hidden" name="next" value="%s">
              <label>用户名 <input name="username" autocomplete="username"></label>
              <label>密码 <input type="password" name="password" autocomplete="current-password"></label>
              <button type="submit">登录</button>
            </form>"""
            % (escape(get_token(request)), escape(next_url)),
            content_type="text/html; charset=utf-8",
        )

    def post(self, request: HttpRequest) -> HttpResponse:
        user = authenticate(
            request,
            username=request.POST.get("username", ""),
            password=request.POST.get("password", ""),
        )
        if user is None or not user.is_active:
            return _json_error("access_denied", "用户名或密码错误。", status=401)
        login(request, user)
        next_url = request.POST.get("next", "/")
        parsed = urlparse(next_url)
        if not url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ) and parsed.netloc:
            next_url = "/"
        return redirect(next_url)


__all__ = [
    "AuthorizationServerMetadataView",
    "MCPAuthorizationView",
    "MCPLoginView",
    "MCPTokenView",
    "ProtectedResourceMetadataView",
    "RevokeTokenView",
]
