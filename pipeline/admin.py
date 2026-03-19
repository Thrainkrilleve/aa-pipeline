"""
Pipeline Django Admin

Provides clean, functional admin interfaces for:
  - OnboardingFlow (with inline steps and checks)
  - FlowStep (standalone, for cross-flow management)
  - CheckFilter (catalog view)
  - FlowAssignment (with search and status filter)
  - StepCompletion (audit view)

Phase 2 will replace the inline step editor with a custom drag-and-drop
builder view.  For now the TabularInline/StackedInline approach gives
admins full control without leaving the flow change page.
"""

# Standard Library
import json

# Django
from django import forms
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

# Alliance Auth
from allianceauth import hooks
from allianceauth.services.admin import ServicesUserAdmin

from .models import (
    AssignmentStatus,
    CheckFilter,
    FlowAssignment,
    FlowStatus,
    FlowStep,
    OnboardingFlow,
    StepCheck,
    StepCompletion,
    StepType,
)
from .service_registry import get_all_services


# ---------------------------------------------------------------------------
# Inline: StepCheck within FlowStep
# ---------------------------------------------------------------------------


class StepCheckInline(admin.TabularInline):
    model = StepCheck
    extra = 1
    fields = ["order", "filter", "label"]
    ordering = ["order"]
    verbose_name = _("Smart Filter check")
    verbose_name_plural = _("Smart Filter checks")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("filter__content_type")


# ---------------------------------------------------------------------------
# Inline: FlowStep within OnboardingFlow
# ---------------------------------------------------------------------------


class FlowStepInline(admin.StackedInline):
    model = FlowStep
    extra = 0
    fields = [
        "order", "name", "description", "step_type", "optional",
        "body",
        "service_slug", "service_fallback_acknowledgement",
    ]
    ordering = ["order"]
    show_change_link = True

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("checks")


# ---------------------------------------------------------------------------
# OnboardingFlow admin
# ---------------------------------------------------------------------------


@admin.register(OnboardingFlow)
class OnboardingFlowAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "flow_type_badge",
        "status_badge",
        "step_count",
        "assignment_count",
        "auto_assign",
        "updated_at",
    ]
    list_filter = ["status", "flow_type", "auto_assign"]
    search_fields = ["name", "description", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["created_at", "updated_at", "assignment_stats_panel"]
    filter_horizontal = [
        "states",
        "groups",
        "corporations",
        "alliances",
        "factions",
        "characters",
        "on_complete_add_groups",
    ]
    inlines = [FlowStepInline]

    fieldsets = [
        (
            _("Identity"),
            {
                "fields": ["name", "slug", "flow_type", "status", "description"],
            },
        ),
        (
            _("Content"),
            {
                "fields": ["body_complete"],
                "description": _(
                    "Markdown text shown to the user after all required steps are complete."
                ),
            },
        ),
        (
            _("Audience & Visibility"),
            {
                "fields": [
                    "auto_assign",
                    "states",
                    "groups",
                    "corporations",
                    "alliances",
                    "factions",
                    "characters",
                ],
                "description": _(
                    "Choose at least one audience dimension before publishing.  "
                    "A flow with no audience configured is invisible to all users."
                ),
            },
        ),
        (
            _("On-Completion Automation"),
            {
                "fields": ["on_complete_add_groups", "on_complete_webhook_url"],
                "classes": ["collapse"],
                "description": _("Phase 4 — these settings are stored but not yet actioned."),
            },
        ),
        (
            _("Metadata"),
            {
                "fields": ["created_at", "updated_at", "assignment_stats_panel"],
                "classes": ["collapse"],
            },
        ),
    ]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(
                _step_count=Count("steps", distinct=True),
                _assignment_count=Count("assignments", distinct=True),
            )
        )

    @admin.display(description=_("Steps"), ordering="_step_count")
    def step_count(self, obj):
        return obj._step_count

    @admin.display(description=_("Assigned"), ordering="_assignment_count")
    def assignment_count(self, obj):
        return obj._assignment_count

    @admin.display(description=_("Type"))
    def flow_type_badge(self, obj):
        colours = {
            "onboarding": "primary",
            "training": "info",
            "certification": "success",
            "vetting": "warning",
            "industry": "secondary",
            "other": "light",
        }
        colour = colours.get(obj.flow_type, "secondary")
        return format_html(
            '<span class="badge text-bg-{}">{}</span>',
            colour,
            obj.get_flow_type_display(),
        )

    @admin.display(description=_("Status"))
    def status_badge(self, obj):
        colours = {
            FlowStatus.DRAFT: "secondary",
            FlowStatus.PUBLISHED: "success",
            FlowStatus.ARCHIVED: "danger",
        }
        colour = colours.get(obj.status, "secondary")
        return format_html(
            '<span class="badge text-bg-{}">{}</span>',
            colour,
            obj.get_status_display(),
        )

    @admin.display(description=_("Assignment Statistics"))
    def assignment_stats_panel(self, obj):
        if not obj.pk:
            return "—"
        total = obj.assignments.count()
        completed = obj.assignments.filter(status=AssignmentStatus.COMPLETED).count()
        in_progress = obj.assignments.filter(status=AssignmentStatus.IN_PROGRESS).count()
        assigned = obj.assignments.filter(status=AssignmentStatus.ASSIGNED).count()
        return format_html(
            "<table class='table table-sm table-bordered w-auto'>"
            "<tr><th>Total</th><th>Completed</th><th>In Progress</th><th>Not Started</th></tr>"
            "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>"
            "</table>",
            total,
            completed,
            in_progress,
            assigned,
        )


# ---------------------------------------------------------------------------
# FlowStep admin (standalone — useful for cross-flow search)
# ---------------------------------------------------------------------------


@admin.register(FlowStep)
class FlowStepAdmin(admin.ModelAdmin):
    list_display = ["name", "flow", "order", "step_type_badge", "optional"]
    list_filter = ["step_type", "optional", "flow__status"]
    search_fields = ["name", "description", "flow__name"]
    ordering = ["flow__name", "order"]
    inlines = [StepCheckInline]

    fieldsets = [
        (
            None,
            {
                "fields": [
                    "flow", "order", "name", "description",
                    "step_type", "optional", "body",
                ],
            },
        ),
        (
            _("Service Check Settings"),
            {
                "fields": ["service_slug", "service_fallback_acknowledgement"],
                "classes": ["collapse"],
                "description": _(
                    "Only relevant for 'Service Account Check' step type.  "
                    "Available services: "
                    + ", ".join(get_all_services().keys())
                ),
            },
        ),
    ]

    @admin.display(description=_("Type"))
    def step_type_badge(self, obj):
        colours = {
            StepType.FILTER_CHECK: "primary",
            StepType.ACKNOWLEDGEMENT: "info",
            StepType.SERVICE_CHECK: "success",
        }
        colour = colours.get(obj.step_type, "secondary")
        return format_html(
            '<span class="badge text-bg-{}">{}</span>',
            colour,
            obj.get_step_type_display(),
        )


# ---------------------------------------------------------------------------
# CheckFilter admin
# ---------------------------------------------------------------------------


def _get_filter_choices():
    """Return (value, label) choices for all registered Smart Filter objects."""
    choices = [("" , "---------")]
    for app_hook in hooks.get_hooks("secure_group_filters"):
        for filter_model in app_hook():
            ct = ContentType.objects.get_for_model(filter_model)
            label_prefix = f"{ct.app_label}.{ct.model}"
            for obj in filter_model.objects.order_by("pk"):
                choices.append((f"{ct.pk}:{obj.pk}", f"{label_prefix}: {obj}"))
    return choices


class CheckFilterForm(forms.ModelForm):
    """
    Custom form that presents a flat dropdown of all registered Smart Filter
    objects so an admin can register an existing filter into the catalog.
    """

    filter_object_choice = forms.ChoiceField(
        label=_("Smart Filter Object"),
        help_text=_(
            "Select a Smart Filter object to register in the Pipeline catalog.  "
            "Objects already registered are shown but cannot be re-added."
        ),
        choices=[],
    )

    class Meta:
        model = CheckFilter
        fields = []  # content_type / object_id are editable=False; set in save()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        existing = set(
            CheckFilter.objects.exclude(pk=self.instance.pk if self.instance.pk else None)
            .values_list("content_type_id", "object_id")
        )
        choices = [("" , "---------")]
        for app_hook in hooks.get_hooks("secure_group_filters"):
            for filter_model in app_hook():
                ct = ContentType.objects.get_for_model(filter_model)
                label_prefix = f"{ct.app_label}.{ct.model}"
                for obj in filter_model.objects.order_by("pk"):
                    value = f"{ct.pk}:{obj.pk}"
                    already = (ct.pk, obj.pk) in existing
                    display = f"{label_prefix}: {obj}" + (" [already registered]" if already else "")
                    choices.append((value, display))
        self.fields["filter_object_choice"].choices = choices
        # Pre-select current binding when editing
        if self.instance.pk:
            self.fields["filter_object_choice"].initial = (
                f"{self.instance.content_type_id}:{self.instance.object_id}"
            )

    def clean_filter_object_choice(self):
        value = self.cleaned_data.get("filter_object_choice")
        if not value:
            raise forms.ValidationError(_("Please select a Smart Filter object."))
        try:
            ct_pk, obj_pk = value.split(":")
            int(ct_pk); int(obj_pk)
        except (ValueError, TypeError):
            raise forms.ValidationError(_("Invalid selection."))
        return value

    def save(self, commit=True):
        value = self.cleaned_data["filter_object_choice"]
        ct_pk, obj_pk = value.split(":")
        self.instance.content_type_id = int(ct_pk)
        self.instance.object_id = int(obj_pk)
        return super().save(commit=commit)


@admin.register(CheckFilter)
class CheckFilterAdmin(admin.ModelAdmin):
    form = CheckFilterForm
    list_display = ["__str__", "content_type", "object_id"]
    search_fields = ["content_type__app_label", "content_type__model"]
    readonly_fields = []

    def has_change_permission(self, request, obj=None):
        # Editing an existing entry is effectively re-pointing it; allow it.
        return super().has_change_permission(request, obj)


# ---------------------------------------------------------------------------
# FlowAssignment admin
# ---------------------------------------------------------------------------


@admin.register(FlowAssignment)
class FlowAssignmentAdmin(ServicesUserAdmin):
    search_fields = ServicesUserAdmin.search_fields + ("flow__name",)
    list_display = ServicesUserAdmin.list_display + (
        "flow",
        "status_badge",
        "assigned_at",
        "completed_at",
    )
    list_filter = ["status", "flow"]
    readonly_fields = ["assigned_at", "completed_at"]
    actions = ["mark_completed", "reset_to_assigned"]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("flow", "user__profile")
        )

    @admin.display(description=_("Status"))
    def status_badge(self, obj):
        colours = {
            AssignmentStatus.ASSIGNED: "secondary",
            AssignmentStatus.IN_PROGRESS: "primary",
            AssignmentStatus.COMPLETED: "success",
        }
        colour = colours.get(obj.status, "secondary")
        return format_html(
            '<span class="badge text-bg-{}">{}</span>',
            colour,
            obj.get_status_display(),
        )

    @admin.action(description=_("Mark selected assignments as completed"))
    def mark_completed(self, request, queryset):
        from django.utils import timezone

        updated = queryset.filter(status__in=[AssignmentStatus.ASSIGNED, AssignmentStatus.IN_PROGRESS]).update(
            status=AssignmentStatus.COMPLETED,
            completed_at=timezone.now(),
        )
        self.message_user(request, _(f"{updated} assignment(s) marked as completed."))

    @admin.action(description=_("Reset selected assignments to 'Assigned'"))
    def reset_to_assigned(self, request, queryset):
        updated = queryset.update(
            status=AssignmentStatus.ASSIGNED,
            completed_at=None,
        )
        self.message_user(request, _(f"{updated} assignment(s) reset."))


# ---------------------------------------------------------------------------
# StepCompletion admin
# ---------------------------------------------------------------------------


@admin.register(StepCompletion)
class StepCompletionAdmin(admin.ModelAdmin):
    search_fields = (
        "assignment__user__username",
        "assignment__flow__name",
        "step__name",
    )
    list_display = (
        "user_display",
        "flow_name",
        "step",
        "completed_at",
        "metadata_preview",
    )
    list_filter = ["assignment__flow", "step__step_type"]
    ordering = ["-completed_at"]
    readonly_fields = ["completed_at", "assignment", "step", "completed_by", "metadata"]
    list_select_related = True

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("assignment__flow", "assignment__user", "step")
        )

    @admin.display(description=_("User"), ordering="assignment__user__username")
    def user_display(self, obj):
        return obj.assignment.user.username

    @admin.display(description=_("Flow"), ordering="assignment__flow__name")
    def flow_name(self, obj):
        return obj.assignment.flow.name

    @admin.display(description=_("Metadata"))
    def metadata_preview(self, obj):
        if not obj.metadata:
            return "—"
        try:
            snippet = json.dumps(obj.metadata)[:80]
            return mark_safe(f"<code>{snippet}…</code>") if len(snippet) == 80 else mark_safe(f"<code>{snippet}</code>")
        except Exception:
            return "—"
