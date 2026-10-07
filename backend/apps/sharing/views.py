from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from backend.apps.applications.models import JobApplication
from backend.apps.applications.pagination import JobApplicationPagination
from .models import SharingRequest
from .serializers import (
    ConnectionsSerializer, CreateRequestSerializer, RecommendationsSerializer,
    RequestHistorySerializer, RespondRequestSerializer, SharedApplicationPageSerializer,
    SharedApplicationSerializer, SharingErrorSerializer, SharingRequestSerializer, SharingUserSerializer,
)


class SharingFailure(APIException):
    def __init__(self, code, message, status_code, details=None):
        self.status_code = status_code
        super().__init__({"code": code, "message": message, "details": details or {}})


def not_found():
    raise SharingFailure("NOT_FOUND", "未找到用户、申请或有效共享。", 404)


def conflict():
    raise SharingFailure("SHARING_CONFLICT", "申请或共享状态已变化，请刷新后重试。", 409)


def positive_id(value):
    if not isinstance(value, str) or not value.isascii() or not value.isdigit() or int(value) < 1:
        raise SharingFailure("VALIDATION_ERROR", "用户 ID 必须是正整数。", 400)
    # IDs outside the database bigint range cannot identify an existing user.
    result = int(value)
    if result > 9223372036854775807:
        not_found()
    return result


def active_user(user_id, viewer):
    user_id = positive_id(str(user_id))
    if user_id == viewer.pk:
        not_found()
    user = get_user_model().objects.filter(pk=user_id, is_active=True).first()
    if user is None:
        not_found()
    return user


def validated(serializer):
    if not serializer.is_valid():
        raise SharingFailure("VALIDATION_ERROR", "请求参数校验失败。", 400, serializer.errors)
    return serializer.validated_data


ERRORS = {code: SharingErrorSerializer for code in (400, 401, 404, 409)}


class SharingAPIView(APIView):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def handle_exception(self, exc):
        response = super().handle_exception(exc)
        if response is not None and isinstance(response.data, dict):
            codes = {400: "VALIDATION_ERROR", 401: "UNAUTHORIZED", 403: "FORBIDDEN", 404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED", 409: "SHARING_CONFLICT"}
            response.data.setdefault("code", codes.get(response.status_code, "INTERNAL_ERROR"))
            response.data.setdefault("message", str(response.data.get("detail", "请求无法完成。")))
            response.data.setdefault("details", {})
        return response

    def user_data(self, value, *, many=False):
        return SharingUserSerializer(value, many=many, context={"request": self.request}).data

    def request_data(self, value, *, many=False):
        return SharingRequestSerializer(value, many=many, context={"request": self.request}).data


class MeView(SharingAPIView):
    @extend_schema(responses={200: SharingUserSerializer, 401: SharingErrorSerializer})
    def get(self, request):
        return Response(self.user_data(request.user))


class RecommendationsView(SharingAPIView):
    @extend_schema(responses={200: RecommendationsSerializer, 401: SharingErrorSerializer})
    def get(self, request):
        pairs = SharingRequest.objects.filter(Q(sender=request.user) | Q(recipient=request.user), status__in=("pending", "accepted"))
        excluded = {request.user.pk}
        for sender_id, recipient_id in pairs.values_list("sender_id", "recipient_id"):
            excluded.update((sender_id, recipient_id))
        users = list(get_user_model().objects.filter(is_active=True).exclude(pk__in=excluded).order_by("?")[:settings.SHARING_RECOMMENDATION_COUNT])
        return Response({"count": len(users), "results": self.user_data(users, many=True)})


class UserView(SharingAPIView):
    @extend_schema(responses={200: SharingUserSerializer, **ERRORS})
    def get(self, request, user_id):
        return Response(self.user_data(active_user(user_id, request.user)))


class RequestsView(SharingAPIView):
    @extend_schema(responses={200: RequestHistorySerializer, 401: SharingErrorSerializer})
    def get(self, request):
        rows = SharingRequest.objects.select_related("sender", "recipient").order_by("-created_at", "-id")
        return Response({
            "incoming": self.request_data(rows.filter(recipient=request.user)[:100], many=True),
            "outgoing": self.request_data(rows.filter(sender=request.user)[:100], many=True),
        })

    @extend_schema(request=CreateRequestSerializer, responses={201: SharingRequestSerializer, **ERRORS})
    def post(self, request):
        data = validated(CreateRequestSerializer(data=request.data))
        target_id = data["recipient_id"]
        if target_id == request.user.pk:
            raise SharingFailure("VALIDATION_ERROR", "不能向自己申请互看。", 400)
        target = active_user(target_id, request.user)
        low, high = sorted((request.user.pk, target.pk))
        try:
            with transaction.atomic():
                # Lock both users in consistent order to serialize creation,
                # including opposite directions when no request yet exists.
                members = list(get_user_model().objects.select_for_update().filter(pk__in=(low, high)).order_by("pk"))
                if len(members) != 2 or any(not member.is_active for member in members):
                    not_found()
                if SharingRequest.objects.filter(lower_user_id=low, higher_user_id=high, status__in=("pending", "accepted")).exists():
                    conflict()
                item = SharingRequest.objects.create(sender=request.user, recipient=target, lower_user_id=low, higher_user_id=high)
        except IntegrityError:
            conflict()
        return Response(self.request_data(item), status=201)


class RespondView(SharingAPIView):
    @extend_schema(request=RespondRequestSerializer, responses={200: SharingRequestSerializer, **ERRORS})
    def post(self, request, request_id):
        with transaction.atomic():
            item = SharingRequest.objects.select_for_update().filter(pk=positive_id(request_id), recipient=request.user, sender__is_active=True).first()
            if item is None:
                not_found()
            decision = validated(RespondRequestSerializer(data=request.data))["decision"]
            if item.status != "pending":
                conflict()
            item.status = decision
            item.responded_at = timezone.now()
            item.save(update_fields=["status", "responded_at"])
            return Response(self.request_data(item))


class ConnectionsView(SharingAPIView):
    @extend_schema(responses={200: ConnectionsSerializer, 401: SharingErrorSerializer})
    def get(self, request):
        items = SharingRequest.objects.select_related("sender", "recipient").filter(Q(sender=request.user) | Q(recipient=request.user), status="accepted", sender__is_active=True, recipient__is_active=True)
        return Response({"results": [
            {"id": item.pk, "user": self.user_data(item.recipient if item.sender_id == request.user.pk else item.sender), "created_at": item.responded_at}
            for item in items
        ]})


class RevokeView(SharingAPIView):
    @extend_schema(responses={204: None, **ERRORS})
    def delete(self, request, connection_id):
        with transaction.atomic():
            item = SharingRequest.objects.select_for_update().filter(Q(sender=request.user) | Q(recipient=request.user), pk=positive_id(connection_id), status="accepted").first()
            if item is None:
                not_found()
            item.status = "revoked"
            item.responded_at = timezone.now()
            item.save(update_fields=["status", "responded_at"])
        return Response(status=204)


class SharedApplicationsView(SharingAPIView):
    @extend_schema(
        parameters=[OpenApiParameter("page", OpenApiTypes.INT), OpenApiParameter("page_size", OpenApiTypes.INT, enum=[10, 20, 50, 100]), OpenApiParameter("search", OpenApiTypes.STR)],
        responses={200: SharedApplicationPageSerializer, **ERRORS},
    )
    def get(self, request, user_id):
        target = active_user(user_id, request.user)
        low, high = sorted((request.user.pk, target.pk))
        if not SharingRequest.objects.filter(lower_user_id=low, higher_user_id=high, status="accepted").exists():
            not_found()
        queryset = JobApplication.objects.filter(user=target).select_related("company").order_by("-updated_at", "-id")
        search = request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(Q(company__company_name__icontains=search) | Q(company_name__icontains=search) | Q(position_name__icontains=search))
        paginator = JobApplicationPagination()
        try:
            page = paginator.paginate_queryset(queryset, request, view=self)
        except ValidationError as exc:
            raise SharingFailure("VALIDATION_ERROR", "分页参数校验失败。", 400, exc.detail.get("details", {})) from exc
        return paginator.get_paginated_response(SharedApplicationSerializer(page, many=True).data)
