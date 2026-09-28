import secrets

from django.conf import settings
from django.db import models


AVATARS = tuple(f"avatar-{index:02d}" for index in range(1, 9))


def random_avatar():
    return secrets.choice(AVATARS)


class SharingProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sharing_profile")
    avatar = models.CharField(max_length=9, choices=[(value, value) for value in AVATARS], default=random_avatar)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(avatar__in=AVATARS), name="sharing_valid_avatar")]


class SharingRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "待同意"
        ACCEPTED = "accepted", "已同意"
        REJECTED = "rejected", "已拒绝"
        REVOKED = "revoked", "已解除"

    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sharing_sent_requests")
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sharing_received_requests")
    # Canonical unordered pair supports a database-level cross-direction guard.
    lower_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sharing_lower_requests")
    higher_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sharing_higher_requests")
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(lower_user__lt=models.F("higher_user")), name="sharing_pair_order"),
            models.CheckConstraint(
                condition=(models.Q(sender=models.F("lower_user"), recipient=models.F("higher_user")) | models.Q(sender=models.F("higher_user"), recipient=models.F("lower_user"))),
                name="sharing_pair_members",
            ),
            models.CheckConstraint(condition=models.Q(status__in=("pending", "accepted", "rejected", "revoked")), name="sharing_valid_status"),
            models.CheckConstraint(condition=(models.Q(status="pending", responded_at__isnull=True) | (~models.Q(status="pending") & models.Q(responded_at__isnull=False))), name="sharing_response_time"),
            models.UniqueConstraint(fields=["lower_user", "higher_user"], condition=models.Q(status__in=("pending", "accepted")), name="sharing_one_live_pair"),
        ]
        indexes = [models.Index(fields=["sender", "-created_at"]), models.Index(fields=["recipient", "-created_at"])]
