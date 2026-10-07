from django.urls import path

from .views import CompanyDetailView, CompanyListCreateView


urlpatterns = [
    path("", CompanyListCreateView.as_view(), name="company-list-create"),
    path("<int:pk>/", CompanyDetailView.as_view(), name="company-detail"),
]
