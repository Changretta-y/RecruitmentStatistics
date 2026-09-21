from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers


class RegistrationSerializer(serializers.Serializer):
    username = serializers.CharField(
        min_length=3,
        max_length=30,
        trim_whitespace=True,
    )
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    password = serializers.CharField(
        min_length=8,
        write_only=True,
        trim_whitespace=False,
    )
    password_confirm = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    error_code: str | None = None

    def validate(self, attrs: dict[str, str]) -> dict[str, str]:
        if attrs["password"] != attrs["password_confirm"]:
            self.error_code = "PASSWORDS_DO_NOT_MATCH"
            raise serializers.ValidationError(
                {"password_confirm": ["Passwords do not match."]}
            )

        user_model = get_user_model()
        candidate = user_model(
            username=attrs["username"],
            email=attrs.get("email", ""),
        )
        try:
            validate_password(attrs["password"], user=candidate)
        except DjangoValidationError:
            self.error_code = "WEAK_PASSWORD"
            raise serializers.ValidationError(
                {"password": ["Password does not meet security requirements."]}
            ) from None

        attrs.pop("password_confirm")
        return attrs

    def create(self, validated_data: dict[str, str]):
        user_model = get_user_model()
        return user_model.objects.create_user(**validated_data)


class PublicUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ("id", "username", "email", "date_joined")
        read_only_fields = fields


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class CurrentUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ("id", "username", "email")
        read_only_fields = fields
