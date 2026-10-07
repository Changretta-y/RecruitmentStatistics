from django.http import Http404
from django.db import IntegrityError, transaction
from django.db.models import F, Min, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import serializers
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, OpenApiTypes, extend_schema, extend_schema_view

from backend.config.schema import ErrorResponse
from .models import ApplicationPosition, Company, JobApplication, PositionInterview, current_stage_for_position, normalize_company_name
from .flows import sync_projection
from .pagination import CompanyPagination, JobApplicationPagination
from .serializers import CompanySerializer, InterviewSerializer, JobApplicationSerializer, PositionReadSerializer


application_query_parameters = [
    OpenApiParameter("page", OpenApiTypes.INT, OpenApiParameter.QUERY, required=False),
    OpenApiParameter("page_size", OpenApiTypes.INT, OpenApiParameter.QUERY, required=False),
    OpenApiParameter("search", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
    OpenApiParameter(
        "application_status",
        OpenApiTypes.STR,
        OpenApiParameter.QUERY,
        required=False,
        description="按状态筛选；多个状态使用逗号分隔，也支持重复参数。",
    ),
    OpenApiParameter("stage", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
    OpenApiParameter("application_time_after", OpenApiTypes.DATETIME, OpenApiParameter.QUERY, required=False),
    OpenApiParameter("application_time_before", OpenApiTypes.DATETIME, OpenApiParameter.QUERY, required=False),
    OpenApiParameter("ordering", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
]


class CompanyListCreateView(generics.ListCreateAPIView):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)
    serializer_class = CompanySerializer
    pagination_class = CompanyPagination

    def get_queryset(self):
        queryset = Company.objects.all()
        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(company_name__icontains=search)
        ordering = self.request.query_params.get("ordering")
        allowed = {"company_name", "-company_name", "created_at", "-created_at"}
        if ordering is None:
            return queryset.order_by("company_name", "id")
        terms = [term.strip() for term in ordering.split(",") if term.strip()]
        if not terms or any(term not in allowed for term in terms):
            raise ValidationError({"code": "VALIDATION_ERROR", "details": {"ordering": ["ordering contains an invalid field."]}})
        return queryset.order_by(*terms, "id")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({"code": "VALIDATION_ERROR", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        try:
            with transaction.atomic():
                company = serializer.save()
        except IntegrityError:
            normalized = normalize_company_name(request.data.get("company_name", ""))
            existing = Company.objects.filter(normalized_name=normalized).first()
            if existing is None:
                raise
            return Response(
                {
                    "code": "COMPANY_EXISTS",
                    "message": "公司已存在，请选择现有公司。",
                    "details": {
                        "company_id": existing.pk,
                        "company": CompanySerializer(existing).data,
                    },
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(CompanySerializer(company).data, status=status.HTTP_201_CREATED)


class CompanyDetailView(generics.RetrieveUpdateAPIView):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)
    serializer_class = CompanySerializer
    queryset = Company.objects.all()

    def retrieve(self, request, *args, **kwargs):
        try:
            return super().retrieve(request, *args, **kwargs)
        except Http404:
            return Response({"code": "NOT_FOUND", "message": "未找到公司。", "details": {}}, status=404)

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except Http404:
            return Response({"code": "NOT_FOUND", "message": "未找到公司。", "details": {}}, status=404)
        serializer = self.get_serializer(instance, data=request.data, partial=kwargs.pop("partial", False))
        if not serializer.is_valid():
            return Response({"code": "VALIDATION_ERROR", "details": serializer.errors}, status=400)
        try:
            updated = serializer.save()
        except IntegrityError:
            return Response({"code": "VALIDATION_ERROR", "details": {"company_name": ["该公司名称已存在。"]}}, status=400)
        return Response(CompanySerializer(updated).data)


@extend_schema_view(
    list=extend_schema(
        parameters=application_query_parameters,
        responses={200: JobApplicationSerializer, 400: OpenApiResponse(ErrorResponse), 401: OpenApiResponse(ErrorResponse)},
    ),
    create=extend_schema(
        request=JobApplicationSerializer,
        responses={201: JobApplicationSerializer, 400: OpenApiResponse(ErrorResponse), 401: OpenApiResponse(ErrorResponse)},
    ),
)
class JobApplicationListCreateView(generics.ListCreateAPIView):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)
    serializer_class = JobApplicationSerializer
    pagination_class = JobApplicationPagination
    ordering_stage_fields = {
        "assessment": "assessment_time",
        "ai_interview": "ai_interview_time",
        "written_test": "written_test_time",
        "first_interview": "first_interview_time",
        "second_interview": "second_interview_time",
        "third_interview": "third_interview_time",
        "hr_interview": "hr_interview_time",
    }
    ordering_fields = frozenset(
        {
            "created_at",
            "updated_at",
            "application_time",
        *ordering_stage_fields.values(),
        }
    )

    @extend_schema(
        parameters=application_query_parameters,
        responses={200: JobApplicationSerializer, 400: OpenApiResponse(ErrorResponse), 401: OpenApiResponse(ErrorResponse)},
    )
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = JobApplication.objects.filter(user=self.request.user).select_related("company").annotate(assessment_time=Min("shared_stages__scheduled_at", filter=Q(shared_stages__type="assessment"))).prefetch_related("positions__interviews", "shared_stages")
        params = self.request.query_params

        search = params.get("search")
        if search:
            queryset = queryset.filter(
                Q(company__company_name__icontains=search)
                | Q(company_name__icontains=search)
                | Q(position_name__icontains=search)
                | Q(positions__position_name__icontains=search)
            )

        raw_application_statuses = params.getlist("application_status")
        application_statuses = [
            status.strip()
            for raw_statuses in raw_application_statuses
            for status in raw_statuses.split(",")
            if status.strip()
        ]
        if raw_application_statuses:
            allowed_statuses = {value for value, _label in JobApplication.Status.choices}
            invalid_status = next(
                (status for status in application_statuses if status not in allowed_statuses),
                None,
            )
            if invalid_status is not None or not application_statuses:
                self._validation_error(
                    "application_status",
                    "application_status must contain one or more supported statuses.",
                )
            matching_company_ids = []
            for company in queryset:
                positions = list(company.positions.all())
                shared_stages = list(company.shared_stages.all())
                if any(
                    current_stage_for_position(position, shared_stages=shared_stages) in application_statuses
                    for position in positions
                ) or (not positions and company.application_status in application_statuses):
                    matching_company_ids.append(company.pk)
            queryset = queryset.filter(pk__in=matching_company_ids)

        if "stage" in params:
            self._validation_error(
                "stage",
                "stage is no longer an application business-status filter.",
            )

        application_time_after = self._parse_datetime(
            "application_time_after",
            params.get("application_time_after"),
        )
        if application_time_after is not None:
            queryset = queryset.filter(Q(application_time__gte=application_time_after) | Q(positions__application_time__gte=application_time_after))

        application_time_before = self._parse_datetime(
            "application_time_before",
            params.get("application_time_before"),
        )
        if application_time_before is not None:
            queryset = queryset.filter(Q(application_time__lte=application_time_before) | Q(positions__application_time__lte=application_time_before))

        queryset = queryset.distinct()
        raw_ordering = params.get("ordering")
        if self._uses_default_ordering(raw_ordering):
            applications = list(queryset)
            applications.sort(key=self._default_order_key)
            return applications
        return queryset.order_by(*self._ordering(raw_ordering))

    @staticmethod
    def _uses_default_ordering(raw_ordering):
        return raw_ordering is None or raw_ordering == "-updated_at"

    @staticmethod
    def _is_rejected_company(company):
        positions = list(company.positions.all())
        if positions:
            shared_stages = list(company.shared_stages.all())
            return all(
                current_stage_for_position(position, shared_stages=shared_stages)
                == JobApplication.Status.REJECTED
                for position in positions
            )

        return (
            getattr(company, "current_stage", None) or company.application_status
        ) == JobApplication.Status.REJECTED

    @classmethod
    def _default_order_key(cls, company):
        updated_at = company.updated_at
        updated_timestamp = updated_at.timestamp() if updated_at is not None else float("-inf")
        return (
            1 if cls._is_rejected_company(company) else 0,
            -updated_timestamp,
            -company.pk,
        )

    @staticmethod
    def _validation_error(field, message):
        raise ValidationError(
            {
                "code": "VALIDATION_ERROR",
                "details": {field: [message]},
            }
        )

    def _parse_datetime(self, field, value):
        if value is None:
            return None
        try:
            return serializers.DateTimeField().to_internal_value(value)
        except serializers.ValidationError:
            self._validation_error(field, f"{field} must be a valid ISO 8601 datetime.")

    def _ordering(self, raw_ordering):
        if raw_ordering is None:
            return (
                F("updated_at").desc(nulls_last=True),
                F("id").desc(),
            )
        if not raw_ordering:
            self._validation_error("ordering", "ordering contains an invalid field.")

        ordering = []
        for term in raw_ordering.split(","):
            descending = term.startswith("-")
            field = term[1:] if descending else term
            if field not in self.ordering_fields:
                self._validation_error(
                    "ordering",
                    "ordering contains an invalid field.",
                )
            expression = F(field)
            ordering.append(
                expression.desc(nulls_last=True)
                if descending
                else expression.asc(nulls_last=True)
            )
        ordering.append(F("id").desc())
        return tuple(ordering)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "code": "VALIDATION_ERROR",
                    "details": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@extend_schema_view(
    retrieve=extend_schema(responses={200: JobApplicationSerializer, 401: OpenApiResponse(ErrorResponse), 404: OpenApiResponse(ErrorResponse)}),
    update=extend_schema(request=JobApplicationSerializer, responses={200: JobApplicationSerializer, 400: OpenApiResponse(ErrorResponse), 401: OpenApiResponse(ErrorResponse), 404: OpenApiResponse(ErrorResponse)}),
    partial_update=extend_schema(request=JobApplicationSerializer, responses={200: JobApplicationSerializer, 400: OpenApiResponse(ErrorResponse), 401: OpenApiResponse(ErrorResponse), 404: OpenApiResponse(ErrorResponse)}),
    destroy=extend_schema(responses={204: OpenApiResponse(description="Application deleted."), 401: OpenApiResponse(ErrorResponse), 404: OpenApiResponse(ErrorResponse)}),
)
class JobApplicationDetailView(generics.RetrieveUpdateDestroyAPIView):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)
    serializer_class = JobApplicationSerializer

    def get_queryset(self):
        return JobApplication.objects.filter(user=self.request.user).select_related("company").prefetch_related("positions__interviews", "shared_stages")

    @extend_schema(
        responses={200: JobApplicationSerializer, 401: OpenApiResponse(ErrorResponse), 404: OpenApiResponse(ErrorResponse)},
    )
    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    @extend_schema(
        request=JobApplicationSerializer,
        responses={200: JobApplicationSerializer, 400: OpenApiResponse(ErrorResponse), 401: OpenApiResponse(ErrorResponse), 404: OpenApiResponse(ErrorResponse)},
    )
    def patch(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    @extend_schema(
        responses={204: OpenApiResponse(description="Application deleted."), 401: OpenApiResponse(ErrorResponse), 404: OpenApiResponse(ErrorResponse)},
    )
    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)

    @extend_schema(
        responses={200: JobApplicationSerializer, 401: OpenApiResponse(ErrorResponse), 404: OpenApiResponse(ErrorResponse)},
    )
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except Http404:
            return Response(
                {"code": "NOT_FOUND", "message": "未找到投递记录。", "details": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @extend_schema(
        request=JobApplicationSerializer,
        responses={200: JobApplicationSerializer, 400: OpenApiResponse(ErrorResponse), 401: OpenApiResponse(ErrorResponse), 404: OpenApiResponse(ErrorResponse)},
    )
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        try:
            instance = self.get_object()
        except Http404:
            return Response(
                {"code": "NOT_FOUND", "message": "未找到投递记录。", "details": {}},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial,
        )
        if not serializer.is_valid():
            return Response(
                {
                    "code": "VALIDATION_ERROR",
                    "details": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        self.perform_update(serializer)
        return Response(serializer.data)

    @extend_schema(
        responses={204: OpenApiResponse(description="Application deleted."), 401: OpenApiResponse(ErrorResponse), 404: OpenApiResponse(ErrorResponse)},
    )
    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except Http404:
            return Response(
                {"code": "NOT_FOUND", "message": "未找到投递记录。", "details": {}},
                status=status.HTTP_404_NOT_FOUND,
            )

        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PositionDeleteView(APIView):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request, company_id, position_id):
        company = get_object_or_404(JobApplication.objects.select_related("company"), pk=company_id, user=request.user)
        position = get_object_or_404(ApplicationPosition, pk=position_id, company=company)
        return Response(PositionReadSerializer(position).data)

    @transaction.atomic
    def delete(self, request, company_id, position_id):
        company = get_object_or_404(JobApplication.objects.select_for_update(), pk=company_id, user=request.user)
        position = get_object_or_404(ApplicationPosition, pk=position_id, company=company)
        if company.positions.count() <= 1:
            return Response({"code": "VALIDATION_ERROR", "details": {"positions": ["公司至少保留一个岗位。"]}}, status=400)
        position.delete()
        sync_projection(company)
        return Response(status=204)


class InterviewResourceView(APIView):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def mutate(self, request, company_id, position_id, interview_id=None):
        company = get_object_or_404(JobApplication.objects.select_for_update(), pk=company_id, user=request.user)
        position = get_object_or_404(ApplicationPosition, pk=position_id, company=company)
        interview = get_object_or_404(PositionInterview, pk=interview_id, position=position) if interview_id is not None else None
        if request.method == "GET":
            return Response(InterviewSerializer(interview).data)
        if request.method == "DELETE":
            interview.delete()
            sync_projection(company)
            return Response(status=204)
        serializer = InterviewSerializer(interview, data=request.data, partial=request.method == "PATCH")
        if not serializer.is_valid():
            return Response({"code": "VALIDATION_ERROR", "details": serializer.errors}, status=400)
        serializer.save(position=position)
        company.flow_version = 2
        sync_projection(company)
        return Response(serializer.data, status=201 if request.method == "POST" else 200)

    def post(self, request, company_id, position_id):
        return self.mutate(request, company_id, position_id)

    def get(self, request, company_id, position_id, interview_id):
        return self.mutate(request, company_id, position_id, interview_id)

    def patch(self, request, company_id, position_id, interview_id):
        return self.mutate(request, company_id, position_id, interview_id)

    def delete(self, request, company_id, position_id, interview_id):
        return self.mutate(request, company_id, position_id, interview_id)


class InterviewCreateView(InterviewResourceView):
    http_method_names = ["post", "options"]


class InterviewDetailView(InterviewResourceView):
    http_method_names = ["get", "patch", "delete", "options"]
