"""
Pipeline Views

index           — list all flows visible to the user (assigned + available)
flow_detail     — render a flow with sidebar navigation and step content
step_action     — POST endpoint for acknowledgements / service-check fallback
dashboard       — lightweight hook used by the AA dashboard
"""

# Standard Library
import logging

# Django
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

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
from .forms import FlowForm, FlowStepForm, StepCheckForm

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ALLOWED_TAGS = [
    "p", "br", "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "blockquote", "pre", "code",
    "strong", "em", "b", "i", "a", "hr", "table",
    "thead", "tbody", "tr", "th", "td",
]
_ALLOWED_ATTRS = {
    "a": ["href", "title", "rel"],
    "img": ["src", "alt", "title"],
}


def render_markdown(text: str) -> str:
    """
    Render *text* as Markdown HTML if the 'markdown' package is available.
    Falls back to Django's ``linebreaks`` filter for plain text.

    Output is always sanitised via Bleach when available.
    """
    if not text:
        return ""
    try:
        import markdown as md

        html = md.markdown(
            text,
            extensions=["fenced_code", "tables", "nl2br", "toc"],
            output_format="html",
        )
        try:
            import bleach
            import bleach.linkifier

            return bleach.clean(html, tags=_ALLOWED_TAGS, attributes=_ALLOWED_ATTRS)
        except ImportError:
            # bleach not available — markdown without sanitisation
            return html
    except ImportError:
        # markdown not available — plain text with Django linebreaks
        from django.utils.html import escape, linebreaks as lb

        return lb(escape(text))


def _build_step_list(user, flow: OnboardingFlow, assignment: FlowAssignment) -> list:
    """
    Return an ordered list of dicts describing each step's state for *user*.

    Each dict:
        step            FlowStep instance
        complete        bool — is this step complete?
        effective_type  str  — resolved step type (may differ from step.step_type
                               for service_check with no installed service)
        check_details   list of {check, label, passed} for filter_check steps
        pct             float (0.0–1.0) partial completion percentage
        body_html       str  — pre-rendered HTML from step.body markdown
        url             str  — URL to navigate directly to this step
    """
    steps = []
    for step in flow.steps.order_by("order"):
        complete = step.is_complete(user, assignment)
        etype = step.effective_type
        steps.append(
            {
                "step": step,
                "complete": complete,
                "effective_type": etype,
                "check_details": step.get_check_details(user),
                "pct": step.get_completion_pct(user, assignment),
                "body_html": render_markdown(step.body),
                "url": reverse(
                    "pipeline:flow_detail_step",
                    kwargs={"slug": flow.slug, "step_pk": step.pk},
                ),
            }
        )
    return steps


def _first_incomplete(steps: list) -> dict | None:
    """Return the first non-optional incomplete step, or None if all done."""
    for s in steps:
        if not s["complete"] and not s["step"].optional:
            return s
    return None


def _get_or_create_assignment(flow: OnboardingFlow, user) -> FlowAssignment:
    assignment, created = FlowAssignment.objects.get_or_create(
        flow=flow,
        user=user,
        defaults={"status": AssignmentStatus.ASSIGNED},
    )
    return assignment


# ---------------------------------------------------------------------------
# Dashboard widget
# ---------------------------------------------------------------------------


def pipeline_dashboard(request) -> str:
    """
    Render the dashboard hook snippet.

    Returns an HTML string (not a full response) so Alliance Auth can embed it
    on the dashboard alongside other app widgets.
    """
    if not request.user.is_authenticated:
        return ""
    if not request.user.has_perm("pipeline.basic_access"):
        return ""

    assigned = OnboardingFlow.objects.get_assigned_for_user(request.user).order_by(
        "name"
    )

    items = []
    for flow in assigned:
        assignment = FlowAssignment.objects.filter(
            flow=flow, user=request.user
        ).first()
        if assignment is None:
            continue
        total = flow.steps.count()
        completed = sum(
            1
            for s in flow.steps.all()
            if s.is_complete(request.user, assignment)
        )
        items.append(
            {
                "flow": flow,
                "assignment": assignment,
                "total": total,
                "completed": completed,
                "pct": int(completed / total * 100) if total else 100,
            }
        )

    if not items:
        return ""

    return render_to_string(
        "pipeline/dashboard.html",
        {"pipeline_items": items},
        request=request,
    )


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------


@login_required
@permission_required("pipeline.basic_access")
def index(request: WSGIRequest) -> HttpResponse:
    """List all flows visible (or assigned) to the current user."""
    user = request.user

    assigned_flows = OnboardingFlow.objects.get_assigned_for_user(user).order_by("name")
    visible_flows = (
        OnboardingFlow.objects.get_visible_for_user(user)
        .exclude(assignments__user=user)
        .order_by("name")
    )

    def _enrich(qs):
        result = []
        for flow in qs:
            assignment = FlowAssignment.objects.filter(flow=flow, user=user).first()
            total = flow.steps.count()
            if assignment:
                completed = sum(
                    1
                    for s in flow.steps.all()
                    if s.is_complete(user, assignment)
                )
            else:
                completed = 0
            result.append(
                {
                    "flow": flow,
                    "assignment": assignment,
                    "total": total,
                    "completed": completed,
                    "pct": int(completed / total * 100) if total else 100,
                }
            )
        return result

    context = {
        "assigned_items": _enrich(assigned_flows),
        "available_items": _enrich(visible_flows),
    }
    return render(request, "pipeline/index.html", context)


# ---------------------------------------------------------------------------
# Flow detail
# ---------------------------------------------------------------------------


@login_required
@permission_required("pipeline.basic_access")
def flow_detail(
    request: WSGIRequest, slug: str, step_pk: int | None = None
) -> HttpResponse:
    """
    Render a flow for the current user.

    Published flows are accessible to any eligible user.  Draft flows are
    accessible only to staff / superusers for preview purposes.
    """
    user = request.user

    flow = get_object_or_404(OnboardingFlow, slug=slug)

    # Access control -------------------------------------------------------
    if flow.status == FlowStatus.DRAFT:
        if not (user.is_staff or user.is_superuser or _can_manage(user)):
            raise PermissionDenied(
                "This flow is not published yet.  Only staff may preview it."
            )
    elif flow.status == FlowStatus.ARCHIVED:
        raise PermissionDenied("This flow has been archived.")
    elif not flow.is_visible_to_user(user) and not FlowAssignment.objects.filter(
        flow=flow, user=user
    ).exists():
        raise PermissionDenied("You do not have access to this flow.")

    assignment = _get_or_create_assignment(flow, user)
    steps = _build_step_list(user, flow, assignment)

    # Determine which step to show -----------------------------------------
    current = None
    if step_pk:
        # Navigating to a specific step
        current = next((s for s in steps if s["step"].pk == step_pk), None)
    if current is None:
        # Default to first incomplete required step
        current = _first_incomplete(steps)

    # Check overall completion ---------------------------------------------
    all_required_done = all(
        s["complete"] for s in steps if not s["step"].optional
    )

    if all_required_done and assignment.status != AssignmentStatus.COMPLETED:
        assignment.recalculate_status()

    # Completion body text -------------------------------------------------
    complete_body_html = ""
    if all_required_done:
        body = flow.body_complete or ""
        # Simple template variable substitution for {{ user }} and {{ character }}
        main_char = getattr(getattr(user, "profile", None), "main_character", None)
        char_name = getattr(main_char, "character_name", user.username) if main_char else user.username
        body = body.replace("{{ user }}", user.username).replace(
            "{{ character }}", char_name
        )
        complete_body_html = render_markdown(body)

    total_steps = len(steps)
    completed_count = sum(1 for s in steps if s["complete"])
    total_pct = int(completed_count / total_steps * 100) if total_steps else 100

    # First incomplete required step (for "Next" CTA when viewing a completed step)
    next_step = _first_incomplete(steps)

    context = {
        "flow": flow,
        "assignment": assignment,
        "steps": steps,
        "current": current,
        "next_step": next_step,
        "all_complete": all_required_done,
        "complete_body_html": complete_body_html,
        "total_pct": total_pct,
        "completed_count": completed_count,
        "total_count": total_steps,
        "page_title": flow.name,
    }
    return render(request, "pipeline/flow_detail.html", context)


# ---------------------------------------------------------------------------
# Step action (POST)
# ---------------------------------------------------------------------------


@login_required
@permission_required("pipeline.basic_access")
def step_action(request: WSGIRequest, slug: str, step_pk: int) -> HttpResponse:
    """
    Handle step-completion actions submitted via POST.

    Supported actions (sent as ``action`` in POST body):
        acknowledge     — mark an acknowledgement step complete
        refresh         — re-evaluate filter checks (GET-equivalent, no state change)
    """
    if request.method != "POST":
        return redirect("pipeline:flow_detail", slug=slug)

    user = request.user
    flow = get_object_or_404(OnboardingFlow.objects.filter(status=FlowStatus.PUBLISHED), slug=slug)

    # Verify access
    if not flow.is_visible_to_user(user) and not FlowAssignment.objects.filter(
        flow=flow, user=user
    ).exists():
        raise PermissionDenied

    step = get_object_or_404(FlowStep, pk=step_pk, flow=flow)
    assignment = _get_or_create_assignment(flow, user)
    action = request.POST.get("action", "refresh")

    if action == "acknowledge":
        etype = step.effective_type
        if etype not in (StepType.ACKNOWLEDGEMENT,):
            logger.warning(
                "Pipeline: acknowledge action on non-acknowledgement step pk=%s", step_pk
            )
        else:
            if not StepCompletion.objects.filter(
                assignment=assignment, step=step
            ).exists():
                # Capture a truncated snapshot of the body for the GDPR metadata field
                body_snapshot = (step.body or "")[:500]
                StepCompletion.objects.create(
                    assignment=assignment,
                    step=step,
                    completed_by=user,
                    metadata={"acknowledged_body_preview": body_snapshot},
                )
                assignment.recalculate_status()
                messages.success(request, _("Step acknowledged."))
            else:
                messages.info(request, _("You have already acknowledged this step."))

    elif action == "service_confirm":
        # Manual fallback confirmation when service is not installed
        etype = step.effective_type
        if etype == StepType.ACKNOWLEDGEMENT and step.step_type == StepType.SERVICE_CHECK:
            StepCompletion.objects.get_or_create(
                assignment=assignment,
                step=step,
                defaults={"completed_by": user, "metadata": {"service_fallback": True}},
            )
            assignment.recalculate_status()
            messages.success(request, _("Service confirmed."))

    # Redirect to the same step (allows filter-check refresh) or next step
    return redirect(
        reverse(
            "pipeline:flow_detail_step",
            kwargs={"slug": slug, "step_pk": step_pk},
        )
    )


# ---------------------------------------------------------------------------
# Flow Manager (in-app admin UI)
# ---------------------------------------------------------------------------

def _can_manage(user) -> bool:
    """True if the user may access the flow manager."""
    return user.is_superuser or user.has_perm("pipeline.manage_flows")


def _require_manage(view_func):
    """Decorator: must be logged in AND have manage_flows or be superuser."""
    from functools import wraps

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        if not _can_manage(request.user):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return _wrapped


@_require_manage
def manage_index(request: WSGIRequest) -> HttpResponse:
    """List all flows with management actions."""
    flows = (
        OnboardingFlow.objects
        .annotate(
            step_count=Count("steps", distinct=True),
            active_count=Count(
                "assignments",
                distinct=True,
                filter=Q(assignments__status__in=["assigned", "in_progress"]),
            ),
            completed_count=Count(
                "assignments",
                distinct=True,
                filter=Q(assignments__status="completed"),
            ),
        )
        .order_by("name")
    )
    context = {
        "flows": flows,
        "page_title": _("Manage Flows"),
        "can_manage": True,
    }
    return render(request, "pipeline/manage/index.html", context)


@_require_manage
def manage_flow_create(request: WSGIRequest) -> HttpResponse:
    """Create a new flow."""
    if request.method == "POST":
        form = FlowForm(request.POST)
        if form.is_valid():
            flow = form.save()
            messages.success(request, _(f'Flow "{flow.name}" created successfully.'))
            return redirect("pipeline:manage_flow_edit", slug=flow.slug)
    else:
        form = FlowForm()

    context = {
        "form": form,
        "page_title": _("Create Flow"),
        "action_label": _("Create Flow"),
        "cancel_url": reverse("pipeline:manage_index"),
    }
    return render(request, "pipeline/manage/flow_form.html", context)


@_require_manage
def manage_flow_edit(request: WSGIRequest, slug: str) -> HttpResponse:
    """Edit an existing flow and manage its steps."""
    flow = get_object_or_404(OnboardingFlow, slug=slug)

    if request.method == "POST":
        form = FlowForm(request.POST, instance=flow)
        if form.is_valid():
            form.save()
            messages.success(request, _(f'Flow "{flow.name}" saved.'))
            return redirect("pipeline:manage_flow_edit", slug=flow.slug)
    else:
        form = FlowForm(instance=flow)

    steps = flow.steps.order_by("order")
    context = {
        "form": form,
        "flow": flow,
        "steps": steps,
        "page_title": _(f"Edit: {flow.name}"),
        "action_label": _("Save Changes"),
        "cancel_url": reverse("pipeline:manage_index"),
    }
    return render(request, "pipeline/manage/flow_form.html", context)


@_require_manage
def manage_flow_delete(request: WSGIRequest, slug: str) -> HttpResponse:
    """Confirm and delete a flow."""
    flow = get_object_or_404(OnboardingFlow, slug=slug)

    if request.method == "POST":
        name = flow.name
        flow.delete()
        messages.success(request, _(f'Flow "{name}" deleted.'))
        return redirect("pipeline:manage_index")

    context = {
        "flow": flow,
        "page_title": _(f"Delete: {flow.name}"),
    }
    return render(request, "pipeline/manage/flow_confirm_delete.html", context)


@_require_manage
def manage_step_create(request: WSGIRequest, slug: str) -> HttpResponse:
    """Add a new step to a flow."""
    flow = get_object_or_404(OnboardingFlow, slug=slug)
    next_order = (flow.steps.order_by("-order").values_list("order", flat=True).first() or -1) + 1

    if request.method == "POST":
        form = FlowStepForm(request.POST)
        if form.is_valid():
            step = form.save(commit=False)
            step.flow = flow
            step.save()
            messages.success(request, _(f'Step "{step.name}" added.'))
            return redirect("pipeline:manage_flow_edit", slug=flow.slug)
    else:
        form = FlowStepForm(initial={"order": next_order})

    context = {
        "form": form,
        "flow": flow,
        "page_title": _(f"Add Step to: {flow.name}"),
        "action_label": _("Add Step"),
        "cancel_url": reverse("pipeline:manage_flow_edit", kwargs={"slug": slug}),
    }
    return render(request, "pipeline/manage/step_form.html", context)


@_require_manage
def manage_step_edit(request: WSGIRequest, slug: str, step_pk: int) -> HttpResponse:
    """Edit an existing step."""
    flow = get_object_or_404(OnboardingFlow, slug=slug)
    step = get_object_or_404(FlowStep, pk=step_pk, flow=flow)

    if request.method == "POST":
        form = FlowStepForm(request.POST, instance=step)
        if form.is_valid():
            form.save()
            messages.success(request, _(f'Step "{step.name}" updated.'))
            return redirect("pipeline:manage_flow_edit", slug=flow.slug)
    else:
        form = FlowStepForm(instance=step)

    checks = step.checks.select_related("filter__content_type").order_by("order")
    check_form = StepCheckForm(initial={"order": (checks.values_list("order", flat=True).last() or -1) + 1})
    has_filters = CheckFilter.objects.exists()

    context = {
        "form": form,
        "flow": flow,
        "step": step,
        "checks": checks,
        "check_form": check_form,
        "has_filters": has_filters,
        "page_title": _(f"Edit Step: {step.name}"),
        "action_label": _("Save Step"),
        "cancel_url": reverse("pipeline:manage_flow_edit", kwargs={"slug": slug}),
    }
    return render(request, "pipeline/manage/step_form.html", context)


@_require_manage
def manage_step_check_add(request: WSGIRequest, slug: str, step_pk: int) -> HttpResponse:
    """Add a StepCheck (smart filter) to a filter_check step."""
    if request.method != "POST":
        return redirect("pipeline:manage_step_edit", slug=slug, step_pk=step_pk)

    flow = get_object_or_404(OnboardingFlow, slug=slug)
    step = get_object_or_404(FlowStep, pk=step_pk, flow=flow)
    form = StepCheckForm(request.POST)
    if form.is_valid():
        check = form.save(commit=False)
        check.step = step
        check.save()
        messages.success(request, _("Smart filter check added."))
    else:
        for field_errors in form.errors.values():
            for error in field_errors:
                messages.error(request, error)
    return redirect("pipeline:manage_step_edit", slug=slug, step_pk=step_pk)


@_require_manage
def manage_step_check_delete(request: WSGIRequest, slug: str, step_pk: int, check_pk: int) -> HttpResponse:
    """Remove a StepCheck from a step."""
    if request.method != "POST":
        return redirect("pipeline:manage_step_edit", slug=slug, step_pk=step_pk)

    flow = get_object_or_404(OnboardingFlow, slug=slug)
    step = get_object_or_404(FlowStep, pk=step_pk, flow=flow)
    check = get_object_or_404(StepCheck, pk=check_pk, step=step)
    check.delete()
    messages.success(request, _("Smart filter check removed."))
    return redirect("pipeline:manage_step_edit", slug=slug, step_pk=step_pk)


@_require_manage
def manage_step_delete(request: WSGIRequest, slug: str, step_pk: int) -> HttpResponse:
    """Confirm and delete a step."""
    flow = get_object_or_404(OnboardingFlow, slug=slug)
    step = get_object_or_404(FlowStep, pk=step_pk, flow=flow)

    if request.method == "POST":
        name = step.name
        step.delete()
        messages.success(request, _(f'Step "{name}" deleted.'))
        return redirect("pipeline:manage_flow_edit", slug=flow.slug)

    context = {
        "flow": flow,
        "step": step,
        "page_title": _(f"Delete Step: {step.name}"),
    }
    return render(request, "pipeline/manage/step_confirm_delete.html", context)


@_require_manage
def manage_flow_publish(request: WSGIRequest, slug: str) -> HttpResponse:
    """Quick-action: cycle a flow's status (draft → published → draft; archived → draft)."""
    if request.method != "POST":
        return redirect("pipeline:manage_index")
    flow = get_object_or_404(OnboardingFlow, slug=slug)
    if flow.status == FlowStatus.PUBLISHED:
        flow.status = FlowStatus.DRAFT
        flow.save(update_fields=["status"])
        messages.info(request, _(f'"{flow.name}" set back to Draft.'))
    elif flow.status == FlowStatus.ARCHIVED:
        flow.status = FlowStatus.DRAFT
        flow.save(update_fields=["status"])
        messages.info(request, _(f'"{flow.name}" restored to Draft.'))
    else:
        flow.status = FlowStatus.PUBLISHED
        flow.save(update_fields=["status"])
        messages.success(request, _(f'"{flow.name}" published.'))
    return redirect("pipeline:manage_index")


@_require_manage
def manage_step_reorder(request: WSGIRequest, slug: str, step_pk: int, direction: str) -> HttpResponse:
    """Move a step one position up or down in the flow's step order."""
    if request.method != "POST":
        return redirect("pipeline:manage_flow_edit", slug=slug)
    flow = get_object_or_404(OnboardingFlow, slug=slug)
    step = get_object_or_404(FlowStep, pk=step_pk, flow=flow)
    ordered = list(flow.steps.order_by("order"))
    idx = next((i for i, s in enumerate(ordered) if s.pk == step.pk), None)
    if idx is None:
        return redirect("pipeline:manage_flow_edit", slug=slug)

    if direction == "up" and idx > 0:
        neighbour = ordered[idx - 1]
    elif direction == "down" and idx < len(ordered) - 1:
        neighbour = ordered[idx + 1]
    else:
        return redirect("pipeline:manage_flow_edit", slug=slug)

    # Swap order values
    step.order, neighbour.order = neighbour.order, step.order
    FlowStep.objects.bulk_update([step, neighbour], ["order"])
    return redirect("pipeline:manage_flow_edit", slug=slug)

