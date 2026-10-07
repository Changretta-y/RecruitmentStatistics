from rest_framework import serializers
from datetime import timezone
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.exceptions import NotFound

from .models import ApplicationPosition, INTERVIEW_NAMES, JobApplication, PositionInterview, SHARED_TYPES, SharedStage
from .flows import bootstrap_legacy, sync_legacy_write, sync_projection


class LegacyJobApplicationSerializer(serializers.ModelSerializer):
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
        if isinstance(data, dict) and 'current_stage' in data:
            raise serializers.ValidationError({'current_stage': ['该字段不可写。']})
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


def reject_fields(data, allowed):
    if not isinstance(data, dict):
        raise serializers.ValidationError({'non_field_errors': ['必须是 JSON 对象。']})
    errors = {key: ['该字段不可写。'] for key in data if key not in allowed}
    if errors:
        raise serializers.ValidationError(errors)


class ScheduleSerializer(serializers.Serializer):
    scheduled_at = serializers.DateTimeField(allow_null=True, required=False, default_timezone=timezone.utc)
    duration_minutes = serializers.IntegerField(min_value=1, max_value=1440, allow_null=True, required=False)

    def to_internal_value(self, data):
        reject_fields(data, self.fields)
        duration = data.get('duration_minutes')
        if duration is not None and type(duration) is not int:
            raise serializers.ValidationError({'duration_minutes': ['时长必须是 1 到 1440 的整数。']})
        return super().to_internal_value(data)

    def validate(self, attrs):
        when = attrs.get('scheduled_at', getattr(self.instance, 'scheduled_at', None))
        duration = attrs.get('duration_minutes', getattr(self.instance, 'duration_minutes', None))
        if when is None:
            if attrs.get('duration_minutes') is not None:
                raise serializers.ValidationError({'duration_minutes': ['未设置时间时，时长必须为空。']})
            attrs['duration_minutes'] = None
        elif duration is None:
            attrs['duration_minutes'] = getattr(self.instance, 'duration_minutes', None) or 60
        return attrs


class InterviewSerializer(ScheduleSerializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(max_length=200)

    def to_internal_value(self, data):
        if 'id' in data:
            raise serializers.ValidationError({'id': ['ID 由服务器生成。']})
        return super().to_internal_value(data)

    def create(self, validated_data):
        return PositionInterview.objects.create(**validated_data)

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance


class SharedStageSerializer(ScheduleSerializer):
    type = serializers.ChoiceField(choices=SHARED_TYPES)


class PositionFieldsSerializer(serializers.Serializer):
    position_name = serializers.CharField(max_length=200)
    application_url = serializers.URLField(max_length=500, allow_blank=True, required=False)
    application_status = serializers.ChoiceField(choices=JobApplication.Status.choices, required=False)
    application_time = serializers.DateTimeField(allow_null=True, required=False)
    notes = serializers.CharField(allow_blank=True, required=False)

    def to_internal_value(self, data):
        reject_fields(data, self.fields)
        return super().to_internal_value(data)


class PositionReadSerializer(serializers.ModelSerializer):
    interviews = InterviewSerializer(many=True, read_only=True)
    current_stage = serializers.ReadOnlyField()

    class Meta:
        model = ApplicationPosition
        fields = ('id', 'position_name', 'application_url', 'application_status', 'current_stage', 'application_time', 'notes', 'interviews')


class JobApplicationSerializer(LegacyJobApplicationSerializer):
    """The company contract, with flat input support for existing integrations."""
    positions = serializers.JSONField(required=False)
    shared_stages = serializers.JSONField(required=False)

    class Meta(LegacyJobApplicationSerializer.Meta):
        fields = LegacyJobApplicationSerializer.Meta.fields + ('positions', 'shared_stages')

    def validate_company_name(self, value):
        value = super().validate_company_name(value)
        if self.instance and JobApplication.objects.filter(user=self.instance.user, company_name__iexact=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError('该公司已存在，请在已有公司中添加岗位。')
        return value

    def to_internal_value(self, data):
        self.nested_input = 'positions' in data or 'shared_stages' in data or (self.instance is not None and self.instance.flow_version == 2 and not any(key in data for key in ('position_name', 'application_status', *self.date_time_fields, 'notes', 'application_url', *(pair[1] for pair in self.stage_fields))))
        if not self.nested_input:
            return super().to_internal_value(data)
        reject_fields(data, {'company_name', 'positions', 'shared_stages'})
        attrs = {}
        if 'company_name' in data:
            field = serializers.CharField(max_length=200)
            try:
                attrs['company_name'] = field.run_validation(data['company_name'])
            except serializers.ValidationError as exc:
                raise serializers.ValidationError({'company_name': exc.detail}) from exc
        elif self.instance is None:
            raise serializers.ValidationError({'company_name': ['该字段必填。']})
        for key in ('positions', 'shared_stages'):
            if key in data:
                if not isinstance(data[key], list):
                    raise serializers.ValidationError({key: ['必须为数组。']})
                attrs[key] = data[key]
        if self.instance is None and not attrs.get('positions'):
            raise serializers.ValidationError({'positions': ['请至少填写一个岗位。']})
        return attrs

    def validate(self, attrs):
        if not getattr(self, 'nested_input', False):
            return super().validate(attrs)
        if self.instance and 'company_name' in attrs:
            exists = JobApplication.objects.filter(user=self.instance.user, company_name__iexact=attrs['company_name']).exclude(pk=self.instance.pk).exists()
            if exists:
                raise serializers.ValidationError({'company_name': ['该公司已存在，请在已有公司中添加岗位。']})
        positions = []
        seen = set()
        for index, raw in enumerate(attrs.get('positions', [])):
            try:
                reject_fields(raw, {'id', 'position_name', 'application_url', 'application_status', 'application_time', 'notes', 'interviews'})
                position = None
                if 'id' in raw:
                    if self.instance is None or type(raw['id']) is not int:
                        raise serializers.ValidationError({'id': ['不能指定新增岗位 ID。']})
                    if raw['id'] in seen:
                        raise serializers.ValidationError({'id': ['同一岗位不能重复提交。']})
                    seen.add(raw['id'])
                    position = self.instance.positions.filter(pk=raw['id']).first()
                    if position is None:
                        raise NotFound()
                serializer = PositionFieldsSerializer(position, data={key: value for key, value in raw.items() if key not in ('id', 'interviews')}, partial=position is not None)
                serializer.is_valid(raise_exception=True)
                parsed = dict(serializer.validated_data)
                if position:
                    parsed['id'] = position.pk
                if 'interviews' in raw:
                    if not isinstance(raw['interviews'], list):
                        raise serializers.ValidationError({'interviews': ['必须为数组。']})
                    parsed['interviews'] = []
                    interview_ids = set()
                    for child_index, child in enumerate(raw['interviews']):
                        try:
                            reject_fields(child, {'id', 'name', 'scheduled_at', 'duration_minutes'})
                            interview = None
                            if 'id' in child:
                                if position is None or type(child['id']) is not int:
                                    raise serializers.ValidationError({'id': ['不能指定新增面试 ID。']})
                                if child['id'] in interview_ids:
                                    raise serializers.ValidationError({'id': ['同一面试不能重复提交。']})
                                interview_ids.add(child['id'])
                                interview = position.interviews.filter(pk=child['id']).first()
                                if interview is None:
                                    raise NotFound()
                            nested = InterviewSerializer(interview, data={key: value for key, value in child.items() if key != 'id'}, partial=interview is not None)
                            nested.is_valid(raise_exception=True)
                            item = dict(nested.validated_data)
                            if interview:
                                item['id'] = interview.pk
                            parsed['interviews'].append(item)
                        except serializers.ValidationError as exc:
                            raise serializers.ValidationError({'interviews': {child_index: exc.detail}}) from exc
                positions.append(parsed)
            except serializers.ValidationError as exc:
                raise serializers.ValidationError({'positions': {index: exc.detail}}) from exc
        if 'positions' in attrs:
            attrs['positions'] = positions
        stages = []
        staged_values = {}
        for index, raw in enumerate(attrs.get('shared_stages', [])):
            try:
                reject_fields(raw, {'type', 'scheduled_at', 'duration_minutes'})
                kind = raw.get('type')
                if not isinstance(kind, str) or kind not in SHARED_TYPES:
                    raise serializers.ValidationError({'type': ['请选择 AI 面、测评或笔试。']})
                existing = staged_values.get(kind)
                if existing is None:
                    existing = self.instance.shared_stages.filter(type=kind).first() if self.instance else None
                serializer = SharedStageSerializer(existing, data=raw, partial=False)
                serializer.is_valid(raise_exception=True)
                parsed = dict(serializer.validated_data)
                stages.append(parsed)
                staged_values[kind] = SimpleNamespace(type=kind, scheduled_at=parsed.get('scheduled_at', getattr(existing, 'scheduled_at', None)), duration_minutes=parsed.get('duration_minutes', getattr(existing, 'duration_minutes', None)))
            except serializers.ValidationError as exc:
                raise serializers.ValidationError({'shared_stages': {index: exc.detail}}) from exc
        if 'shared_stages' in attrs:
            attrs['shared_stages'] = stages
        return attrs

    def to_representation(self, instance):
        positions = list(instance.positions.all())
        shared_stages = list(instance.shared_stages.all())
        instance._projection_positions = positions
        for position in positions:
            position._projection_shared_stages = shared_stages
        result = super().to_representation(instance)
        result['positions'] = PositionReadSerializer(positions, many=True).data
        stages = {stage.type: stage for stage in shared_stages}
        result['shared_stages'] = [SharedStageSerializer(stages[kind]).data if kind in stages else {'type': kind, 'scheduled_at': getattr(instance, kind + '_time', None), 'duration_minutes': getattr(instance, kind + '_duration_minutes', None)} for kind in SHARED_TYPES]
        return result

    @staticmethod
    def lock_user(user):
        get_user_model().objects.select_for_update().get(pk=user.pk)

    @staticmethod
    def write_children(company, positions, stages):
        for kind in SHARED_TYPES:
            SharedStage.objects.get_or_create(company=company, type=kind)
        for raw in stages:
            values = dict(raw)
            kind = values.pop('type')
            SharedStage.objects.filter(company=company, type=kind).update(**values)
        for raw in positions:
            values = dict(raw)
            interviews = values.pop('interviews', [])
            position_id = values.pop('id', None)
            if position_id:
                position = company.positions.filter(pk=position_id).first()
                if position is None:
                    raise NotFound()
                for key, value in values.items():
                    setattr(position, key, value)
                position.save()
            else:
                position = ApplicationPosition.objects.create(company=company, **values)
            for raw_interview in interviews:
                item = dict(raw_interview)
                interview_id = item.pop('id', None)
                if interview_id:
                    if not position.interviews.filter(pk=interview_id).update(**item):
                        raise NotFound()
                else:
                    PositionInterview.objects.create(position=position, **item)

    @transaction.atomic
    def create(self, validated_data):
        user = validated_data['user']
        self.lock_user(user)
        if not self.nested_input:
            old_company = JobApplication.objects.filter(user=user, company_name__iexact=validated_data['company_name']).first()
            if old_company:
                bootstrap_legacy(old_company)
                position = ApplicationPosition.objects.create(company=old_company, **{key: value for key, value in validated_data.items() if key in PositionFieldsSerializer().fields})
                for kind, name in INTERVIEW_NAMES.items():
                    if validated_data.get(kind + '_time'):
                        PositionInterview.objects.create(position=position, name=name, scheduled_at=validated_data[kind + '_time'], duration_minutes=validated_data.get(kind + '_duration_minutes'))
                for kind in ('ai_interview', 'written_test'):
                    if kind + '_time' in validated_data:
                        SharedStage.objects.update_or_create(company=old_company, type=kind, defaults={'scheduled_at': validated_data[kind + '_time'], 'duration_minutes': validated_data.get(kind + '_duration_minutes')})
                sync_projection(old_company)
                return old_company
            company = super().create(validated_data)
            bootstrap_legacy(company)
            return company
        values = dict(validated_data)
        positions = values.pop('positions')
        stages = values.pop('shared_stages', [])
        company = JobApplication.objects.select_for_update().filter(user=user, company_name__iexact=values['company_name']).first()
        if company is None:
            company = JobApplication.objects.create(**values, flow_version=2)
        else:
            bootstrap_legacy(company)
            company.flow_version = 2
        self.write_children(company, positions, stages)
        sync_projection(company)
        return company

    @transaction.atomic
    def update(self, instance, validated_data):
        self.lock_user(instance.user)
        instance = JobApplication.objects.select_for_update().get(pk=instance.pk)
        if not getattr(self, 'nested_input', False):
            if 'company_name' in validated_data and JobApplication.objects.filter(user=instance.user, company_name__iexact=validated_data['company_name']).exclude(pk=instance.pk).exists():
                raise serializers.ValidationError({'code': 'VALIDATION_ERROR', 'details': {'company_name': ['该公司已存在。']}})
            changed = set(validated_data)
            company = super().update(instance, validated_data)
            sync_legacy_write(company, changed)
            return company
        bootstrap_legacy(instance)
        values = dict(validated_data)
        positions = values.pop('positions', [])
        stages = values.pop('shared_stages', [])
        if 'company_name' in values and JobApplication.objects.filter(user=instance.user, company_name__iexact=values['company_name']).exclude(pk=instance.pk).exists():
            raise serializers.ValidationError({'code': 'VALIDATION_ERROR', 'details': {'company_name': ['该公司已存在。']}})
        for key, value in values.items():
            setattr(instance, key, value)
        instance.flow_version = 2
        self.write_children(instance, positions, stages)
        sync_projection(instance)
        return instance
