import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import NotificationSettings, VerificationToken
from .serializers import NotificationSettingsSerializer


def _settings_for(user, *, lock=False):
    value, _ = NotificationSettings.objects.get_or_create(user=user)
    if lock:
        value = NotificationSettings.objects.select_for_update().get(pk=value.pk)
    return value


def _token_digest(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class NotificationSettingsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        instance = _settings_for(request.user)
        return Response(NotificationSettingsSerializer(instance).data)

    def patch(self, request):
        with transaction.atomic():
            instance = _settings_for(request.user, lock=True)
            serializer = NotificationSettingsSerializer(
                instance, data=request.data, partial=True
            )
            if not serializer.is_valid():
                return Response(
                    {"code": "VALIDATION_ERROR", "details": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            email_changed = (
                "recipient_email" in serializer.validated_data
                and serializer.validated_data["recipient_email"] != instance.recipient_email
            )
            updated = serializer.save()
            if email_changed:
                VerificationToken.objects.filter(user=request.user, active=True).update(
                    active=False
                )
        return Response(NotificationSettingsSerializer(updated).data)


class VerificationRequestView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        with transaction.atomic():
            instance = _settings_for(request.user, lock=True)
            if not instance.recipient_email:
                return Response(
                    {
                        "code": "VALIDATION_ERROR",
                        "details": {"recipient_email": ["请先设置收件邮箱。"]},
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            now = timezone.now()
            threshold = now - timedelta(hours=1)
            attempts = VerificationToken.objects.filter(
                user=request.user,
                recipient_email=instance.recipient_email,
                created_at__gte=threshold,
            ).count()
            if attempts >= 3:
                return Response(
                    {"code": "RATE_LIMITED", "detail": "验证邮件申请次数过多，请稍后重试。"},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

            raw_token = secrets.token_urlsafe(32)
            token_record = VerificationToken.objects.create(
                user=request.user,
                recipient_email=instance.recipient_email,
                token_digest=_token_digest(raw_token),
                created_at=now,
                expires_at=now + timedelta(hours=24),
            )
            link = (
                f"{settings.FRONTEND_BASE_URL}/notification-settings/verify"
                f"?token={raw_token}"
            )
            message = EmailMessage(
                subject="校招进度管理系统：验证收件邮箱",
                body=f"请在 24 小时内打开以下链接验证邮箱：\n{link}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[instance.recipient_email],
            )
            if not settings.EMAIL_HOST.strip():
                token_record.active = False
                token_record.save(update_fields=["active"])
                return Response(
                    {"code": "MAIL_NOT_CONFIGURED", "detail": "邮件服务暂不可用，请稍后重试。"},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            try:
                sent = message.send(fail_silently=False)
            except Exception:
                sent = 0
            if sent != 1:
                token_record.active = False
                token_record.save(update_fields=["active"])
                return Response(
                    {"code": "MAIL_DELIVERY_FAILED", "detail": "验证邮件发送失败，请稍后重试。"},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

        return Response({"detail": "验证邮件已发送。"}, status=status.HTTP_202_ACCEPTED)


class VerifyAddressView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        token = request.data.get("token") if hasattr(request.data, "get") else None
        if not isinstance(token, str) or not token:
            return Response(
                {"code": "VALIDATION_ERROR", "details": {"token": ["此字段为必填项。"]}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        digest = _token_digest(token)
        now = timezone.now()
        with transaction.atomic():
            try:
                record = VerificationToken.objects.select_for_update().get(
                    token_digest=digest,
                    user=request.user,
                    active=True,
                    consumed_at__isnull=True,
                )
            except VerificationToken.DoesNotExist:
                return Response(
                    {"code": "INVALID_VERIFICATION_TOKEN", "detail": "验证链接无效或已使用。"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if record.expires_at <= now:
                record.active = False
                record.save(update_fields=["active"])
                return Response(
                    {"code": "EXPIRED_VERIFICATION_TOKEN", "detail": "验证链接已过期。"},
                    status=status.HTTP_410_GONE,
                )
            instance = NotificationSettings.objects.select_for_update().get(user=request.user)
            if instance.recipient_email != record.recipient_email:
                record.active = False
                record.save(update_fields=["active"])
                return Response(
                    {"code": "INVALID_VERIFICATION_TOKEN", "detail": "验证链接无效或已使用。"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            record.active = False
            record.consumed_at = now
            record.save(update_fields=["active", "consumed_at"])
            instance.verified = True
            instance.save(update_fields=["verified"])

        return Response(NotificationSettingsSerializer(instance).data, status=status.HTTP_200_OK)
