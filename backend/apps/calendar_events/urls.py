from django.urls import path

from .views import CalendarEventsView


urlpatterns = [
    path("calendar/events/", CalendarEventsView.as_view(), name="calendar-events"),
]
