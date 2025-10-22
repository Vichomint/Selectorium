from django.urls import path
from . import views

urlpatterns = [
    path("upload-form/", views.upload_form_view, name="upload_form"),
    path("upload-cv/", views.upload_cv_view, name="upload_cv"),
    path("dashboard/<int:job_id>/", views.recruiter_dashboard, name="recruiter_dashboard"),
    path("job/crear/", views.create_job_view, name="crear_job"),


]