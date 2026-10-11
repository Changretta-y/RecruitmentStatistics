"""OAuth Resource Server verification for the MCP endpoint."""

from __future__ import annotations

import hashlib
import time

from asgiref.sync import sync_to_async
from django.conf import settings
from django.db import close_old_connections
from oauth2_provider.models import get_access_token_model

from mcp.server.auth.provider import AccessToken


def _load_access_token(token: str) -> AccessToken | None:
    # OAuth Toolkit issues opaque tokens.  Reject obvious JWTs and malformed
    # probes before touching the database; this also keeps an invalid bearer
    # challenge independent of database availability.
    if not token or "." in token or len(token) < 20:
        return None
    close_old_connections()
    try:
        checksum = hashlib.sha256(token.encode("utf-8")).hexdigest()
        model = get_access_token_model()
        instance = (
            model.objects.select_related("user", "application")
            .filter(token_checksum=checksum)
            .first()
        )
        if instance is None or instance.is_expired():
            return None
        if instance.user is None or not instance.user.is_active:
            return None

        resources = instance.resource or []
        if resources != [settings.MCP_RESOURCE_URI]:
            return None

        scopes = [scope for scope in instance.scope.split() if scope]
        client_id = "oauth-public-client"
        if instance.application is not None:
            client_id = instance.application.client_id
        return AccessToken(
            token=token,
            client_id=client_id,
            scopes=scopes,
            expires_at=int(instance.expires.timestamp()),
            resource=settings.MCP_RESOURCE_URI,
            subject=str(instance.user_id),
            claims={"iss": settings.MCP_AUTHORIZATION_ISSUER},
        )
    finally:
        close_old_connections()


class MCPTokenVerifier:
    """Adapter from Django OAuth Toolkit's token store to MCP SDK v2."""

    def verify_token_sync(self, token: str) -> AccessToken | None:
        return _load_access_token(token)

    async def verify_token(self, token: str) -> AccessToken | None:
        return await sync_to_async(self.verify_token_sync, thread_sensitive=True)(token)


token_verifier = MCPTokenVerifier()


def token_expired(access_token: AccessToken) -> bool:
    return bool(access_token.expires_at and access_token.expires_at < int(time.time()))
