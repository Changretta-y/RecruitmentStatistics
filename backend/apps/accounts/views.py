from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings as jwt_api_settings
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import OpenApiResponse, extend_schema

from backend.config.schema import ErrorResponse
from .serializers import (
    CurrentUserSerializer,
    LoginSerializer,
    PublicUserSerializer,
    RegistrationSerializer,
)


class RegisterView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        request=RegistrationSerializer,
        responses={
            201: PublicUserSerializer,
            400: OpenApiResponse(ErrorResponse),
            409: OpenApiResponse(ErrorResponse),
        },
        auth=[],
    )
    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            if serializer.error_code:
                return Response(
                    {"code": serializer.error_code},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(
                {
                    "code": "VALIDATION_ERROR",
                    "details": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        username = serializer.validated_data["username"]
        user_model = get_user_model()
        if user_model.objects.filter(username=username).exists():
            return Response(
                {"code": "USERNAME_ALREADY_EXISTS"},
                status=status.HTTP_409_CONFLICT,
            )

        try:
            with transaction.atomic():
                user = serializer.save()
        except IntegrityError:
            if user_model.objects.filter(username=username).exists():
                return Response(
                    {"code": "USERNAME_ALREADY_EXISTS"},
                    status=status.HTTP_409_CONFLICT,
                )
            raise

        return Response(
            PublicUserSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(description="JWT access/refresh and public user."),
            400: OpenApiResponse(ErrorResponse),
            401: OpenApiResponse(ErrorResponse),
        },
        auth=[],
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "code": "VALIDATION_ERROR",
                    "details": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(
            request=request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            return Response(
                {"code": "INVALID_CREDENTIALS"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "access_expires_in": int(
                    jwt_api_settings.ACCESS_TOKEN_LIFETIME.total_seconds()
                ),
                "refresh_expires_in": int(
                    jwt_api_settings.REFRESH_TOKEN_LIFETIME.total_seconds()
                ),
                "user": CurrentUserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class MeView(APIView):
    authentication_classes = (JWTAuthentication,)

    @extend_schema(
        responses={200: CurrentUserSerializer, 401: OpenApiResponse(ErrorResponse)},
    )
    def get(self, request):
        return Response(CurrentUserSerializer(request.user).data)


class RefreshView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    @staticmethod
    def _invalid_refresh_response():
        return Response(
            {"code": "INVALID_REFRESH_TOKEN"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    @extend_schema(
        request={"application/json": {"type": "object", "properties": {"refresh": {"type": "string"}}}},
        responses={200: OpenApiResponse(description="Rotated JWT access/refresh."), 401: OpenApiResponse(ErrorResponse)},
        auth=[],
    )
    def post(self, request):
        if not hasattr(request.data, "get"):
            return self._invalid_refresh_response()

        refresh_value = request.data.get("refresh")
        if not isinstance(refresh_value, str) or not refresh_value:
            return self._invalid_refresh_response()

        try:
            refresh = RefreshToken(refresh_value)
            original_exp = int(refresh["exp"])
            user_id = refresh["user_id"]
            user_model = get_user_model()
            user = user_model.objects.get(pk=user_id)
            if not user.is_active:
                return self._invalid_refresh_response()
        except (
            TokenError,
            KeyError,
            TypeError,
            ValueError,
            get_user_model().DoesNotExist,
        ):
            return self._invalid_refresh_response()

        try:
            with transaction.atomic():
                refresh.blacklist()
                rotated = RefreshToken()
                rotated["user_id"] = user_id
                rotated["exp"] = original_exp
                rotated.outstand()
        except (TokenError, KeyError, TypeError, ValueError):
            return self._invalid_refresh_response()

        return Response(
            {
                "access": str(rotated.access_token),
                "refresh": str(rotated),
                "access_expires_in": int(
                    jwt_api_settings.ACCESS_TOKEN_LIFETIME.total_seconds()
                ),
                "refresh_expires_in": int(
                    jwt_api_settings.REFRESH_TOKEN_LIFETIME.total_seconds()
                ),
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    @staticmethod
    def _invalid_refresh_response():
        return Response(
            {"code": "INVALID_REFRESH_TOKEN"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @extend_schema(
        request={"application/json": {"type": "object", "properties": {"refresh": {"type": "string"}}}},
        responses={204: OpenApiResponse(description="Refresh token blacklisted."), 400: OpenApiResponse(ErrorResponse), 401: OpenApiResponse(ErrorResponse)},
    )
    def post(self, request):
        if not hasattr(request.data, "get"):
            return self._invalid_refresh_response()

        refresh_value = request.data.get("refresh")
        if not isinstance(refresh_value, str) or not refresh_value:
            return self._invalid_refresh_response()

        try:
            refresh = RefreshToken(refresh_value)
        except TokenError as error:
            if str(error) in {"Token is expired", "Token is blacklisted"}:
                return Response(status=status.HTTP_204_NO_CONTENT)
            return self._invalid_refresh_response()

        try:
            if str(refresh["user_id"]) != str(request.user.pk):
                return self._invalid_refresh_response()
            with transaction.atomic():
                refresh.blacklist()
        except (KeyError, TypeError, ValueError, TokenError):
            return self._invalid_refresh_response()

        return Response(status=status.HTTP_204_NO_CONTENT)
