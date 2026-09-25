from rest_framework import serializers

from .models import JobApplication


class JobApplicationSerializer(serializers.ModelSerializer):
    stage_fields = (
        ("ai_interview_time", "ai_interview_duration_minutes"),
        ("written_test_time", "written_test_duration_minutes"),
        ("first_interview_time", "first_interview_duration_minutes"),
        ("second_interview_time", "second_interview_duration_minutes"),
        ("third_interview_time", "third_interview_duration_minutes"),
        ("hr_interview_time", "hr_interview_duration_minutes"),
    )
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
    ai_interview_duration_minutes = serializers.IntegerField(
        min_value=1, max_value=1440, allow_null=True, required=False
    )
    written_test_duration_minutes = serializers.IntegerField(
        min_value=1, max_value=1440, allow_null=True, required=False
    )
    first_interview_duration_minutes = serializers.IntegerField(
        min_value=1, max_value=1440, allow_null=True, required=False
    )
    second_interview_duration_minutes = serializers.IntegerField(
        min_value=1, max_value=1440, allow_null=True, required=False
    )
    third_interview_duration_minutes = serializers.IntegerField(
        min_value=1, max_value=1440, allow_null=True, required=False
    )
    hr_interview_duration_minutes = serializers.IntegerField(
        min_value=1, max_value=1440, allow_null=True, required=False
    )
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
            "application_url",
            "application_status",
            "current_stage",
            "application_time",
            "ai_interview_time",
            "written_test_time",
            "first_interview_time",
            "second_interview_time",
            "third_interview_time",
            "hr_interview_time",
            "ai_interview_duration_minutes",
            "written_test_duration_minutes",
            "first_interview_duration_minutes",
            "second_interview_duration_minutes",
            "third_interview_duration_minutes",
            "hr_interview_duration_minutes",
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

        # JSON numeric strings and floats are not valid duration inputs. DRF's
        # IntegerField intentionally accepts strings for HTML forms, while this
        # API contract requires an integer JSON number.
        duration_type_errors = {
            duration_field: ["时长必须是 1 到 1440 之间的整数。"]
            for _time_field, duration_field in self.stage_fields
            if duration_field in data
            and data[duration_field] is not None
            and (isinstance(data[duration_field], bool) or not isinstance(data[duration_field], int))
        }
        if duration_type_errors:
            raise serializers.ValidationError(duration_type_errors)
        return super().to_internal_value(data)

    def validate(self, attrs):
        errors = {}
        input_data = self.initial_data

        for time_field, duration_field in self.stage_fields:
            time_was_sent = time_field in input_data
            duration_was_sent = duration_field in input_data
            submitted_time = attrs.get(time_field, getattr(self.instance, time_field, None) if self.instance else None)

            if time_was_sent and submitted_time is None:
                if duration_was_sent and attrs.get(duration_field) is not None:
                    errors[duration_field] = ["清空阶段时间时，时长必须同时为 null 或省略。"]
                attrs[duration_field] = None
                continue

            if submitted_time is None:
                if duration_was_sent and attrs.get(duration_field) is not None:
                    errors[duration_field] = ["未设置阶段时间时，时长必须为 null。"]
                attrs[duration_field] = None
                continue

            if duration_was_sent:
                if attrs.get(duration_field) is None:
                    errors[duration_field] = ["设置阶段时间后，时长必须为 1 到 1440 之间的整数。"]
                continue

            previous_time = getattr(self.instance, time_field, None) if self.instance else None
            previous_duration = getattr(self.instance, duration_field, None) if self.instance else None
            if previous_time is not None and previous_duration is not None:
                attrs[duration_field] = previous_duration
            else:
                attrs[duration_field] = 60

        if errors:
            raise serializers.ValidationError(errors)
        return attrs

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
