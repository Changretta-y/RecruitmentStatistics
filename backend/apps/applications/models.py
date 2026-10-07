from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


CURRENT_STAGE_PRIORITY = {
    "assessment": 0,
    "written_test": 1,
    "first_interview": 2,
    "second_interview": 3,
    "other_interview": 4,
    "hr_interview": 5,
}

_INTERVIEW_STAGE_ALIASES = {
    "一面": "first_interview",
    "第一面": "first_interview",
    "第一轮": "first_interview",
    "firstinterview": "first_interview",
    "firstround": "first_interview",
    "round1": "first_interview",
    "1面": "first_interview",
    "二面": "second_interview",
    "第二面": "second_interview",
    "第二轮": "second_interview",
    "secondinterview": "second_interview",
    "secondround": "second_interview",
    "round2": "second_interview",
    "2面": "second_interview",
    "hr面": "hr_interview",
    "hr面试": "hr_interview",
    "hrinterview": "hr_interview",
    "hrround": "hr_interview",
}


def _normalized_interview_name(value):
    return "".join(str(value or "").strip().casefold().split())


def interview_stage_value(name):
    """Map a position interview name to the public application status value."""
    return _INTERVIEW_STAGE_ALIASES.get(_normalized_interview_name(name), "other_interview")


def _schedule_timestamp(value):
    if timezone.is_naive(value):
        value = timezone.make_aware(value, timezone.get_current_timezone())
    return value.timestamp()


class JobApplication(models.Model):
    class Status(models.TextChoices):
        APPLIED = "applied", "投递"
        ASSESSMENT = "assessment", "测评"
        WRITTEN_TEST = "written_test", "笔试"
        FIRST_INTERVIEW = "first_interview", "一面"
        SECOND_INTERVIEW = "second_interview", "二面"
        OTHER_INTERVIEW = "other_interview", "其他轮次"
        HR_INTERVIEW = "hr_interview", "HR面"
        REJECTED = "rejected", "拒绝"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="job_applications",
    )
    company_name = models.CharField(max_length=200)
    flow_version = models.PositiveSmallIntegerField(default=1)
    position_name = models.CharField(max_length=200)
    application_url = models.URLField(max_length=500, blank=True, default="")
    application_status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.APPLIED,
    )
    application_time = models.DateTimeField(null=True, blank=True)
    ai_interview_time = models.DateTimeField(null=True, blank=True)
    written_test_time = models.DateTimeField(null=True, blank=True)
    first_interview_time = models.DateTimeField(null=True, blank=True)
    second_interview_time = models.DateTimeField(null=True, blank=True)
    third_interview_time = models.DateTimeField(null=True, blank=True)
    hr_interview_time = models.DateTimeField(null=True, blank=True)
    ai_interview_duration_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    written_test_duration_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    first_interview_duration_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    second_interview_duration_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    third_interview_duration_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    hr_interview_duration_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "job_applications"
        ordering = ["-updated_at", "-id"]
        indexes = [
            models.Index(fields=["user", "-updated_at"]),
            models.Index(fields=["user", "application_status"]),
            models.Index(fields=["user", "company_name"]),
        ]
        constraints = [models.UniqueConstraint(models.F("user"), models.functions.Lower(models.functions.Trim("company_name")), name="application_unique_company")]

    def clean(self):
        super().clean()
        errors = {}
        for field_name in ("company_name", "position_name"):
            value = getattr(self, field_name, None)
            if value is None:
                continue
            normalized = value.strip()
            if not normalized:
                errors[field_name] = "该字段去除首尾空格后不能为空。"
            else:
                setattr(self, field_name, normalized)
        if errors:
            raise ValidationError(errors)

    @property
    def current_stage(self) -> str:
        """Return the latest read-only projection for the first position."""
        positions = getattr(self, "_projection_positions", None)
        if positions is None:
            positions = self.positions.order_by("id")
        first = next(iter(positions), None)
        return current_stage_for_position(first) if first is not None else self.application_status


SHARED_TYPES = ("ai_interview", "assessment", "written_test")
INTERVIEW_NAMES = {"first_interview": "一面", "second_interview": "二面", "third_interview": "三面", "hr_interview": "HR 面"}
INTERVIEW_TYPES = {name: stage for stage, name in INTERVIEW_NAMES.items()}


class ApplicationPosition(models.Model):
    company = models.ForeignKey(JobApplication, on_delete=models.CASCADE, related_name="positions")
    position_name = models.CharField(max_length=200)
    application_url = models.URLField(max_length=500, blank=True, default="")
    application_status = models.CharField(max_length=30, choices=JobApplication.Status.choices, default="applied")
    application_time = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["id"]


class SharedStage(models.Model):
    company = models.ForeignKey(JobApplication, on_delete=models.CASCADE, related_name="shared_stages")
    type = models.CharField(max_length=20, choices=[(value, value) for value in SHARED_TYPES])
    scheduled_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["id"]
        constraints = [models.UniqueConstraint(fields=["company", "type"], name="application_unique_shared_stage")]


class PositionInterview(models.Model):
    position = models.ForeignKey(ApplicationPosition, on_delete=models.CASCADE, related_name="interviews")
    name = models.CharField(max_length=200)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["id"]


def current_stage_for_position(position, *, shared_stages=None) -> str:
    """Project the latest scheduled shared or position flow into a canonical status."""
    if position.application_status == JobApplication.Status.REJECTED:
        return JobApplication.Status.REJECTED

    if shared_stages is None:
        shared_stages = getattr(position, "_projection_shared_stages", None)
    if shared_stages is None:
        shared_stages = position.company.shared_stages.all()

    candidates = []
    shared_stage_values = {
        "assessment": "assessment",
        "written_test": "written_test",
        "ai_interview": "other_interview",
    }
    for stage in shared_stages:
        if stage.scheduled_at is None:
            continue
        value = shared_stage_values.get(stage.type)
        if value is not None:
            candidates.append((
                _schedule_timestamp(stage.scheduled_at),
                CURRENT_STAGE_PRIORITY[value],
                stage.pk or 0,
                0,
                value,
            ))

    for interview in position.interviews.all():
        if interview.scheduled_at is None:
            continue
        value = interview_stage_value(interview.name)
        candidates.append((
            _schedule_timestamp(interview.scheduled_at),
            CURRENT_STAGE_PRIORITY[value],
            interview.pk or 0,
            1,
            value,
        ))

    if not candidates:
        return position.application_status
    return max(candidates)[-1]


def current_stage_for_company(company) -> str:
    """Return the projection of the company's first/primary position."""
    positions = getattr(company, "_projection_positions", None)
    if positions is None:
        positions = company.positions.order_by("id")
    first = next(iter(positions), None)
    return current_stage_for_position(first) if first is not None else company.application_status


ApplicationPosition.current_stage = property(current_stage_for_position)
