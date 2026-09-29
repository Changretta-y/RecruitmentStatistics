from django.http import Http404
from django.db import transaction
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
from .models import ApplicationPosition, INTERVIEW_NAMES, JobApplication, PositionInterview
from .flows import sync_projection
from .pagination import JobApplicationPagination
from .serializers import InterviewSerializer, JobApplicationSerializer


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
    stage_fields = {
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
            *stage_fields.values(),
        }
    )

    @extend_schema(
        parameters=application_query_parameters,
        responses={200: JobApplicationSerializer, 400: OpenApiResponse(ErrorResponse), 401: OpenApiResponse(ErrorResponse)},
    )
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = JobApplication.objects.filter(user=self.request.user).annotate(assessment_time=Min("shared_stages__scheduled_at", filter=Q(shared_stages__type="assessment"))).prefetch_related("positions__interviews", "shared_stages")
        params = self.request.query_params

        search = params.get("search")
        if search:
            queryset = queryset.filter(
                Q(company_name__icontains=search)
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
            queryset = queryset.filter(Q(application_status__in=application_statuses) | Q(positions__application_status__in=application_statuses))

        stage = params.get("stage")
        if stage is not None:
            stage_field = self.stage_fields.get(stage)
            if stage_field is None:
                self._validation_error(
                    "stage",
                    "stage is not a supported interview stage.",
                )
            if stage in ("ai_interview", "assessment", "written_test"):
                condition = Q(shared_stages__type=stage, shared_stages__scheduled_at__isnull=False)
            else:
                condition = Q(positions__interviews__name=INTERVIEW_NAMES[stage], positions__interviews__scheduled_at__isnull=False)
            if stage != "assessment":
                condition |= Q(**{f"{stage_field}__isnull": False})
            queryset = queryset.filter(condition)

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

        return queryset.distinct().order_by(*self._ordering(params.get("ordering")))

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
        return JobApplication.objects.filter(user=self.request.user).prefetch_related("positions__interviews", "shared_stages")

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

    def patch(self, request, company_id, position_id, interview_id):
        return self.mutate(request, company_id, position_id, interview_id)

    def delete(self, request, company_id, position_id, interview_id):
        return self.mutate(request, company_id, position_id, interview_id)


class InterviewCreateView(InterviewResourceView):
    http_method_names = ["post", "options"]


class InterviewDetailView(InterviewResourceView):
    http_method_names = ["patch", "delete", "options"]
