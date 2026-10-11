from django.urls import include, path

from .oauth_views import (
    AuthorizationServerMetadataView,
    MCPAuthorizationView,
    MCPLoginView,
    MCPTokenView,
    ProtectedResourceMetadataView,
    RevokeTokenView,
)
from .views import MCPView


urlpatterns = [
    # Keep the path-qualified RFC 9728 document below, and expose the root
    # alias as well for MCP hosts that probe the origin-level discovery URL.
    path(".well-known/oauth-protected-resource", ProtectedResourceMetadataView.as_view(), name="mcp-resource-metadata-root"),
    path(".well-known/oauth-protected-resource/mcp", ProtectedResourceMetadataView.as_view(), name="mcp-resource-metadata"),
    path(".well-known/oauth-authorization-server", AuthorizationServerMetadataView.as_view(), name="mcp-authorization-server-metadata"),
    path("oauth/authorize", MCPAuthorizationView.as_view(), name="mcp-authorize"),
    path("oauth/token", MCPTokenView.as_view(), name="mcp-token"),
    path(
        "oauth/",
        include(
            ("backend.apps.mcp.dcr_urls", "oauth2_provider"),
            namespace="oauth2_provider",
        ),
    ),
    path("oauth/revoke", RevokeTokenView.as_view(), name="mcp-revoke"),
    path("oauth/login", MCPLoginView.as_view(), name="mcp-login"),
    path("mcp", MCPView.as_view(), name="mcp-http"),
]
