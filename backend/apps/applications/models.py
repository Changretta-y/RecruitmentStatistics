from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class JobApplication(models.Model):
    class Status(models.TextChoices):
        APPLIED = "applied", "已投递"
        IN_PROGRESS = "in_progress", "流程中"
        OFFER = "offer", "已录用"
        REJECTED = "rejected", "已拒绝"
        WITHDRAWN = "withdrawn", "已放弃"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="job_applications",
    )
    company_name = models.CharField(max_length=200)
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
        if self.application_status in {
            self.Status.OFFER,
            self.Status.REJECTED,
            self.Status.WITHDRAWN,
        }:
            return self.application_status

        stages = (
            ("hr_interview_time", "hr_interview"),
            ("third_interview_time", "third_interview"),
            ("second_interview_time", "second_interview"),
            ("first_interview_time", "first_interview"),
            ("written_test_time", "written_test"),
            ("ai_interview_time", "ai_interview"),
        )
        for field_name, stage_name in stages:
            if getattr(self, field_name) is not None:
                return stage_name
        return "applied"
