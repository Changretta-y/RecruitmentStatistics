from rest_framework import serializers

from .models import Prompt


class PromptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prompt
        fields = ("id", "title", "content", "is_preset", "created_at", "updated_at")
        read_only_fields = ("id", "is_preset", "created_at", "updated_at")

    def validate_title(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("标题不能为空。")
        return value

    def validate_content(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("内容不能为空。")
        return value
