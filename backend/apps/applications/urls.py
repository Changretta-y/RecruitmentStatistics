from django.urls import path

from .views import InterviewCreateView, InterviewDetailView, JobApplicationDetailView, JobApplicationListCreateView, PositionDeleteView


urlpatterns = [
    path("<int:company_id>/positions/<int:position_id>/", PositionDeleteView.as_view(), name="application-position-delete"),
    path("<int:company_id>/positions/<int:position_id>/interviews/", InterviewCreateView.as_view(), name="application-interview-create"),
    path("<int:company_id>/positions/<int:position_id>/interviews/<int:interview_id>/", InterviewDetailView.as_view(), name="application-interview-detail"),
    path("", JobApplicationListCreateView.as_view(), name="application-list-create"),
    path("<int:pk>/", JobApplicationDetailView.as_view(), name="application-detail"),
]
