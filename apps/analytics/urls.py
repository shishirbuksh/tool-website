from django.urls import path
from apps.analytics import views

urlpatterns = [
    path("api/track", views.track_view, name="analytics_track"),
    path("api/analytics/top", views.top_counts, name="analytics_top"),
]
