"""App URLs"""

# Django
from django.urls import path

# Pipeline
from pipeline import views

app_name: str = "pipeline"

urlpatterns = [
    # Index — list of all flows for the current user
    path("", views.index, name="index"),
    # ── In-app Flow Manager — must come before <slug:slug> ───────────────────
    path("manage/", views.manage_index, name="manage_index"),
    path("manage/new/", views.manage_flow_create, name="manage_flow_create"),
    path("manage/<slug:slug>/edit/", views.manage_flow_edit, name="manage_flow_edit"),
    path("manage/<slug:slug>/delete/", views.manage_flow_delete, name="manage_flow_delete"),
    path("manage/<slug:slug>/publish/", views.manage_flow_publish, name="manage_flow_publish"),
    path("manage/<slug:slug>/steps/new/", views.manage_step_create, name="manage_step_create"),
    path(
        "manage/<slug:slug>/steps/<int:step_pk>/edit/",
        views.manage_step_edit,
        name="manage_step_edit",
    ),
    path(
        "manage/<slug:slug>/steps/<int:step_pk>/delete/",
        views.manage_step_delete,
        name="manage_step_delete",
    ),
    path(
        "manage/<slug:slug>/steps/<int:step_pk>/checks/add/",
        views.manage_step_check_add,
        name="manage_step_check_add",
    ),
    path(
        "manage/<slug:slug>/steps/<int:step_pk>/checks/<int:check_pk>/delete/",
        views.manage_step_check_delete,
        name="manage_step_check_delete",
    ),
    path(
        "manage/<slug:slug>/steps/<int:step_pk>/reorder/<str:direction>/",
        views.manage_step_reorder,
        name="manage_step_reorder",
    ),
    # ── Flow detail — slug-based routes (must come after manage/) ────────────
    path("<slug:slug>/", views.flow_detail, name="flow_detail"),
    path(
        "<slug:slug>/step/<int:step_pk>/",
        views.flow_detail,
        name="flow_detail_step",
    ),
    path(
        "<slug:slug>/step/<int:step_pk>/action/",
        views.step_action,
        name="step_action",
    ),
]
