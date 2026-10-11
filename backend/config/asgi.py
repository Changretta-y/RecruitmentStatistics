"""ASGI entry point with the official MCP Streamable HTTP app mounted."""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.config.settings")

import django

django.setup()

from django.core.asgi import get_asgi_application  # noqa: E402

from backend.apps.mcp.server import mcp_asgi_app  # noqa: E402


django_asgi_app = get_asgi_application()


async def application(scope, receive, send):
    """Route MCP traffic to SDK v2 and everything else to Django."""

    # ``streamable_http_app`` owns a StreamableHTTPSessionManager whose
    # task-group is created by the Starlette lifespan context.  The MCP app is
    # dispatched manually below (so that Django can serve the rest of the
    # project), which means Starlette would otherwise never receive the
    # process-level lifespan events from Uvicorn.  Forward lifespan to the
    # actual MCP Starlette app before handling any HTTP requests.
    if scope.get("type") == "lifespan":
        mcp_scope = dict(scope)
        mcp_scope["app"] = mcp_asgi_app
        await mcp_asgi_app(mcp_scope, receive, send)
        return

    path = scope.get("path", "")
    if path in {"/mcp", "/.well-known/oauth-protected-resource/mcp"}:
        await mcp_asgi_app(scope, receive, send)
        return
    await django_asgi_app(scope, receive, send)
