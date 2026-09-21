from rest_framework import serializers

from .models import JobApplication


class JobApplicationSerializer(serializers.ModelSerializer):
    date_time_fields = (
        "application_time",
        "ai_interview_time",
        "written_test_time",
        "first_interview_time",
        "second_interview_time",
        "third_interview_time",
        "hr_interview_time",
    )

    user = serializers.PrimaryKeyRelatedField(read_only=True)
    application_status = serializers.ChoiceField(
        choices=JobApplication.Status.choices,
        default=JobApplication.Status.APPLIED,
    )
    current_stage = serializers.ReadOnlyField()
    id = serializers.IntegerField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = JobApplication
        fields = (
            "id",
            "user",
            "company_name",
            "position_name",
            "application_status",
            "current_stage",
            "application_time",
            "ai_interview_time",
            "written_test_time",
            "first_interview_time",
            "second_interview_time",
            "third_interview_time",
            "hr_interview_time",
            "notes",
            "created_at",
            "updated_at",
        )

    def to_internal_value(self, data):
        blank_datetime_errors = {
            field: ["此时间字段不能是空字符串；请使用 ISO 8601 时间或 null。"]
            for field in self.date_time_fields
            if field in data and data[field] == ""
        }
        if blank_datetime_errors:
            raise serializers.ValidationError(blank_datetime_errors)
        return super().to_internal_value(data)

    def validate_company_name(self, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise serializers.ValidationError("公司名称去除首尾空格后不能为空。")
        return normalized

    def validate_position_name(self, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise serializers.ValidationError("岗位名称去除首尾空格后不能为空。")
        return normalized
