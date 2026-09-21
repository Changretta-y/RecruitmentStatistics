"""Reusable OpenAPI response shapes for the public API."""

from drf_spectacular.utils import inline_serializer
from rest_framework import serializers


ErrorResponse = inline_serializer(
    name="ErrorResponse",
    fields={
        "code": serializers.CharField(),
        "details": serializers.DictField(required=False),
    },
)

