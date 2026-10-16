from django.urls import path

from .views import PromptDetailView, PromptListCreateView

urlpatterns = [
    path("", PromptListCreateView.as_view(), name="prompt-list-create"),
    path("<int:pk>/", PromptDetailView.as_view(), name="prompt-detail"),
]
