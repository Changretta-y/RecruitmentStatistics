"""Public health check endpoint."""

from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health(_request):
    """Return the service liveness status."""
    return JsonResponse(
        {"status": "ok"},
        json_dumps_params={"separators": (",", ":")},
    )
