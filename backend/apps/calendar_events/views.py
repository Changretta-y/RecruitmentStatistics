from datetime import date, datetime, time, timedelta
import re
from zoneinfo import ZoneInfo

from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    OpenApiTypes,
    extend_schema,
)
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from backend.apps.applications.models import JobApplication
from backend.config.schema import ErrorResponse


CALENDAR_TIMEZONE_NAME = "Asia/Shanghai"
CALENDAR_TIMEZONE = ZoneInfo(CALENDAR_TIMEZONE_NAME)
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MAX_RANGE_DAYS = 42
MAX_STAGE_DURATION = timedelta(minutes=1440)

STAGES = (
    ("ai_interview_time", "ai_interview_duration_minutes", "ai_interview"),
    ("written_test_time", "written_test_duration_minutes", "written_test"),
    ("first_interview_time", "first_interview_duration_minutes", "first_interview"),
    ("second_interview_time", "second_interview_duration_minutes", "second_interview"),
    ("third_interview_time", "third_interview_duration_minutes", "third_interview"),
    ("hr_interview_time", "hr_interview_duration_minutes", "hr_interview"),
)


class CalendarEventSerializer(serializers.Serializer):
    application_id = serializers.IntegerField()
    company_name = serializers.CharField()
    position_name = serializers.CharField()
    stage = serializers.ChoiceField(choices=[stage for _, _, stage in STAGES])
    start_at = serializers.DateTimeField()
    end_at = serializers.DateTimeField()
    duration_minutes = serializers.IntegerField()


class CalendarEventsResponseSerializer(serializers.Serializer):
    timezone = serializers.CharField()
    start = serializers.DateField()
    end = serializers.DateField()
    events = CalendarEventSerializer(many=True)


class CalendarEventsView(APIView):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        parameters=(
            OpenApiParameter(
                "start",
                OpenApiTypes.DATE,
                OpenApiParameter.QUERY,
                required=True,
                description="包含的起始日期（北京时间）。",
            ),
            OpenApiParameter(
                "end",
                OpenApiTypes.DATE,
                OpenApiParameter.QUERY,
                required=True,
                description="不包含的结束日期（北京时间），与 start 相差 1 到 42 天。",
            ),
        ),
        responses={
            200: CalendarEventsResponseSerializer,
            400: OpenApiResponse(ErrorResponse),
            401: OpenApiResponse(ErrorResponse),
        },
    )
    def get(self, request):
        start_date = self._parse_date(request.query_params.get("start"), "start")
        end_date = self._parse_date(request.query_params.get("end"), "end")

        if end_date == start_date:
            self._validation_error("start", "start must be earlier than end.")
        if end_date < start_date:
            self._validation_error(
                "end", "end must be later than start."
            )
        range_days = (end_date - start_date).days
        if range_days > MAX_RANGE_DAYS:
            self._validation_error("end", "The date range cannot exceed 42 days.")

        window_start = timezone.make_aware(
            datetime.combine(start_date, time.min), CALENDAR_TIMEZONE
        )
        window_end = timezone.make_aware(
            datetime.combine(end_date, time.min), CALENDAR_TIMEZONE
        )

        # Every valid stage duration is at most 24 hours. This database filter
        # fetches only applications that could intersect the requested window;
        # the exact end > window_start condition is then checked per stage.
        possible_start = window_start - MAX_STAGE_DURATION
        candidates = Q()
        for time_field, duration_field, _stage in STAGES:
            candidates |= Q(
                **{
                    f"{time_field}__gt": possible_start,
                    f"{time_field}__lt": window_end,
                    f"{duration_field}__isnull": False,
                }
            )

        applications = (
            JobApplication.objects.filter(user=request.user)
            .filter(candidates)
            .only(
                "id",
                "company_name",
                "position_name",
                *(field for pair in STAGES for field in pair[:2]),
            )
        )

        events = []
        for application in applications:
            for time_field, duration_field, stage in STAGES:
                start_at = getattr(application, time_field)
                duration_minutes = getattr(application, duration_field)
                if start_at is None or duration_minutes is None:
                    continue

                end_at = start_at + timedelta(minutes=duration_minutes)
                if start_at < window_end and end_at > window_start:
                    events.append(
                        {
                            "application_id": application.pk,
                            "company_name": application.company_name,
                            "position_name": application.position_name,
                            "stage": stage,
                            "start_at": start_at,
                            "end_at": end_at,
                            "duration_minutes": duration_minutes,
                        }
                    )

        stage_order = {stage: index for index, (_, _, stage) in enumerate(STAGES)}
        events.sort(
            key=lambda event: (
                event["start_at"],
                event["application_id"],
                stage_order[event["stage"]],
            )
        )
        serialized_events = CalendarEventSerializer(events, many=True).data
        return Response(
            {
                "timezone": CALENDAR_TIMEZONE_NAME,
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "events": serialized_events,
            },
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def _parse_date(raw_value, field):
        if raw_value is None:
            CalendarEventsView._validation_error(field, f"{field} is required.")
        if not DATE_PATTERN.fullmatch(raw_value):
            CalendarEventsView._validation_error(
                field, f"{field} must use YYYY-MM-DD format."
            )
        try:
            return date.fromisoformat(raw_value)
        except ValueError:
            CalendarEventsView._validation_error(field, f"{field} is not a valid date.")

    @staticmethod
    def _validation_error(field, message):
        raise serializers.ValidationError(
            {"code": "VALIDATION_ERROR", "details": {field: [message]}}
        )
