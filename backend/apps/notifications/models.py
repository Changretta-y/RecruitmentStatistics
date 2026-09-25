from django.conf import settings
from django.db import models


class NotificationSettings(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_settings",
    )
    recipient_email = models.EmailField(blank=True, default="")
    daily_time = models.TimeField(null=True, blank=True)
    enabled = models.BooleanField(default=False)
    verified = models.BooleanField(default=False)
    timezone = models.CharField(max_length=64, default="Asia/Shanghai", editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notification_settings"


class DailyDelivery(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "待发送"
        SENDING = "sending", "发送中"
        ACCEPTED = "accepted", "已接受"
        FAILED_RETRYABLE = "failed_retryable", "可重试失败"
        FAILED = "failed", "终态失败"
        UNKNOWN = "unknown", "结果不确定"

    notification_settings = models.ForeignKey(
        NotificationSettings,
        on_delete=models.CASCADE,
        related_name="daily_deliveries",
    )
    delivery_date = models.DateField()
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PENDING)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField(null=True, blank=True)
    error_category = models.CharField(max_length=64, blank=True, default="")
    delivery_id = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notification_daily_deliveries"
        constraints = [
            models.UniqueConstraint(
                fields=("notification_settings", "delivery_date"),
                name="notification_daily_delivery_unique",
            )
        ]
        indexes = [models.Index(fields=("delivery_date", "status"))]


class VerificationToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_verification_tokens",
    )
    recipient_email = models.EmailField()
    token_digest = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "notification_verification_tokens"
        indexes = [
            models.Index(
                fields=["user", "recipient_email", "created_at"],
                name="notificatio_user_id_cb0fb3_idx",
            )
        ]
