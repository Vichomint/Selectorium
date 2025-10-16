from django.urls import path
from . import views

urlpatterns = [
    path("match/<int:job_id>/", views.match_view, name="match_view"),
]
