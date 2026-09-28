from django.urls import path

from .views import ConnectionsView, MeView, RecommendationsView, RequestsView, RespondView, RevokeView, SharedApplicationsView, UserView


urlpatterns = [
    path("me/", MeView.as_view()),
    path("users/recommendations/", RecommendationsView.as_view()),
    path("users/<str:user_id>/", UserView.as_view()),
    path("requests/", RequestsView.as_view()),
    path("requests/<str:request_id>/respond/", RespondView.as_view()),
    path("connections/", ConnectionsView.as_view()),
    path("connections/<str:connection_id>/", RevokeView.as_view()),
    path("users/<str:user_id>/applications/", SharedApplicationsView.as_view()),
]
