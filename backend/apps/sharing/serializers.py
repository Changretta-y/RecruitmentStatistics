from django.contrib.auth import get_user_model
from rest_framework import serializers

from backend.apps.applications.models import JobApplication
from .models import SharingProfile, SharingRequest


class SharingUserSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()
    relationship = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = ("id", "username", "avatar", "relationship")
        read_only_fields = fields

    def get_avatar(self, user) -> str:
        profile, _ = SharingProfile.objects.get_or_create(user=user)
        return profile.avatar

    def get_relationship(self, user) -> str:
        viewer = self.context["request"].user
        if user.pk == viewer.pk:
            return "none"
        low, high = sorted((viewer.pk, user.pk))
        item = SharingRequest.objects.filter(lower_user_id=low, higher_user_id=high, status__in=("pending", "accepted")).first()
        if item is None:
            return "none"
        if item.status == "accepted":
            return "connected"
        return "outgoing_pending" if item.sender_id == viewer.pk else "incoming_pending"


class SharingRequestSerializer(serializers.ModelSerializer):
    sender = SharingUserSerializer(read_only=True)
    recipient = SharingUserSerializer(read_only=True)

    class Meta:
        model = SharingRequest
        fields = ("id", "sender", "recipient", "status", "created_at", "responded_at")
        read_only_fields = fields


class CreateRequestSerializer(serializers.Serializer):
    recipient_id = serializers.IntegerField(min_value=1)

    def validate_recipient_id(self, value):
        if type(self.initial_data.get("recipient_id")) is not int:
            raise serializers.ValidationError("用户 ID 必须是正整数。")
        return value


class RespondRequestSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=("accepted", "rejected"))


class RecommendationsSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    results = SharingUserSerializer(many=True)


class RequestHistorySerializer(serializers.Serializer):
    incoming = SharingRequestSerializer(many=True)
    outgoing = SharingRequestSerializer(many=True)


class ConnectionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    user = SharingUserSerializer()
    created_at = serializers.DateTimeField()


class ConnectionsSerializer(serializers.Serializer):
    results = ConnectionSerializer(many=True)


class SharingErrorSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    details = serializers.DictField()


class SharedApplicationSerializer(serializers.ModelSerializer):
    current_stage = serializers.ReadOnlyField()
    company_name = serializers.SerializerMethodField()
    application_url = serializers.SerializerMethodField()

    def get_company_name(self, instance):
        return instance.company.company_name

    def get_application_url(self, instance):
        return instance.company.recruitment_url

    class Meta:
        model = JobApplication
        fields = (
            "id", "company_name", "position_name", "application_url", "application_status", "current_stage", "application_time",
            "ai_interview_time", "written_test_time", "first_interview_time", "second_interview_time", "third_interview_time", "hr_interview_time",
            "ai_interview_duration_minutes", "written_test_duration_minutes", "first_interview_duration_minutes", "second_interview_duration_minutes", "third_interview_duration_minutes", "hr_interview_duration_minutes",
            "created_at", "updated_at",
        )
        read_only_fields = fields


class SharedApplicationPageSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = SharedApplicationSerializer(many=True)
