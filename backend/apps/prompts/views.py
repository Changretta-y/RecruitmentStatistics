from django.db import transaction
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import Prompt, PromptInitialization
from .pagination import PromptPagination
from .serializers import PromptSerializer


PRESETS = (
    ("自我介绍", "请用 STAR 结构介绍自己，并突出与目标岗位相关的经历。"),
    ("项目经历深挖", "请追问项目中的技术决策、个人贡献、难点与结果。"),
    ("行为面试 STAR", "请围绕冲突、行动和结果提出行为面试问题。"),
)


def ensure_presets(user):
    with transaction.atomic():
        marker, created = PromptInitialization.objects.get_or_create(user=user)
        if created:
            Prompt.objects.bulk_create([
                Prompt(user=user, title=title, content=content, is_preset=True)
                for title, content in PRESETS
            ])


class PromptListCreateView(generics.ListCreateAPIView):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)
    serializer_class = PromptSerializer
    pagination_class = PromptPagination

    def get_queryset(self):
        ensure_presets(self.request.user)
        queryset = Prompt.objects.filter(user=self.request.user).order_by("created_at", "id")
        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(Q(title__icontains=search) | Q(content__icontains=search))
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({"code": "VALIDATION_ERROR", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        instance = serializer.save(user=request.user, is_preset=False)
        return Response(self.get_serializer(instance).data, status=status.HTTP_201_CREATED)


class PromptDetailView(generics.RetrieveUpdateDestroyAPIView):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)
    serializer_class = PromptSerializer

    def get_queryset(self):
        return Prompt.objects.filter(user=self.request.user)

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object(), data=request.data, partial=kwargs.pop("partial", False))
        if not serializer.is_valid():
            return Response({"code": "VALIDATION_ERROR", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(serializer.save()).data)
