"""App URLs"""

# Django
from django.urls import path

# Pipeline
from pipeline import views

app_name: str = "pipeline"

urlpatterns = [
    # Index — list of all flows for the current user
    path("", views.index, name="index"),
    # Flow detail — defaults to first incomplete step
    path("<slug:slug>/", views.flow_detail, name="flow_detail"),
    # Flow detail — navigate directly to a specific step
    path(
        "<slug:slug>/step/<int:step_pk>/",
        views.flow_detail,
        name="flow_detail_step",
    ),
    # Step action POST endpoint
    path(
        "<slug:slug>/step/<int:step_pk>/action/",
        views.step_action,
        name="step_action",
    ),
]
