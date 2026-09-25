import re

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from rest_framework import serializers

from .models import NotificationSettings


_TIME_PATTERN = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


class NotificationSettingsSerializer(serializers.ModelSerializer):
    daily_time = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    verified = serializers.BooleanField(read_only=True)
    timezone = serializers.CharField(read_only=True)
    last_delivery = serializers.SerializerMethodField()

    class Meta:
        model = NotificationSettings
        fields = (
            "recipient_email",
            "daily_time",
            "enabled",
            "verified",
            "timezone",
            "last_delivery",
        )

    def get_last_delivery(self, obj):
        delivery = obj.daily_deliveries.order_by("-delivery_date", "-id").first()
        if delivery is None:
            return None
        return {
            "date": delivery.delivery_date.isoformat(),
            "status": delivery.status,
        }

    def validate_recipient_email(self, value):
        if value in (None, ""):
            return ""
        try:
            validate_email(value)
        except DjangoValidationError:
            raise serializers.ValidationError("请输入有效的邮箱地址。") from None
        return value

    def validate_daily_time(self, value):
        if value in (None, ""):
            return None
        if not isinstance(value, str) or not _TIME_PATTERN.fullmatch(value):
            raise serializers.ValidationError("时间必须使用 24 小时 HH:mm 格式。")
        hour, minute = map(int, value.split(":"))
        return hour, minute

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.daily_time is None:
            data["daily_time"] = None
        else:
            data["daily_time"] = instance.daily_time.strftime("%H:%M")
        return data

    def update(self, instance, validated_data):
        time_parts = validated_data.pop("daily_time", serializers.empty)
        if time_parts is not serializers.empty:
            if time_parts is None:
                instance.daily_time = None
            else:
                from datetime import time

                instance.daily_time = time(*time_parts)
        return super().update(instance, validated_data)

    def validate(self, attrs):
        current_email = self.instance.recipient_email if self.instance else ""
        email = attrs.get("recipient_email", current_email)
        if email != current_email:
            attrs["verified"] = False
            if attrs.get("enabled") is not True:
                attrs["enabled"] = False

        enabled = attrs.get("enabled", self.instance.enabled if self.instance else False)
        daily_time = attrs.get("daily_time", self.instance.daily_time if self.instance else None)
        if enabled:
            errors = {}
            if not email:
                errors["recipient_email"] = ["启用通知前请设置收件邮箱。"]
            if not (self.instance and self.instance.verified and email == current_email):
                errors["enabled"] = ["请先验证当前收件邮箱。"]
            if daily_time in (None, ""):
                errors["daily_time"] = ["启用通知前请设置每日发送时间。"]
            if errors:
                raise serializers.ValidationError(errors)
        return attrs
