"""
Pipeline — Structured Journey System for Alliance Auth.

Models
------
CheckFilter         Smart Filter binding (reuses the secure-groups catalog pattern).
OnboardingFlow      A named, typed flow with visibility rules and status lifecycle.
FlowStep            An ordered step inside a flow (filter_check | acknowledgement | service_check).
StepCheck           Binds a Smart Filter to a filter_check FlowStep.
FlowAssignment      Tracks which users are assigned to which flows.
StepCompletion      Records completion of self-guided steps (acknowledgement / service_check fallback).
General             Unmanaged meta-model that holds app-level permissions.
"""

# Standard Library
import functools
import logging

# Django
from django.contrib.auth.models import Group, User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# Alliance Auth
from allianceauth.authentication.models import State
from allianceauth.eveonline.models import (
    EveAllianceInfo,
    EveCharacter,
    EveCorporationInfo,
    EveFactionInfo,
)

from .managers import FlowManager

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Permissions meta-model
# ---------------------------------------------------------------------------


class General(models.Model):
    """Unmanaged model used solely to hold app-level permissions."""

    class Meta:
        managed = False
        default_permissions = ()
        permissions = (
            ("basic_access", "Can access this app"),
            ("manage_flows", "Can create and manage flows"),
        )


# ---------------------------------------------------------------------------
# Smart Filter catalog (identical to allianceauth-secure-groups / workflows)
# ---------------------------------------------------------------------------


class CheckFilter(models.Model):
    """
    A generic reference to any installed Smart Filter object.

    Smart Filters are registered by third-party apps (e.g. allianceauth-secure-groups)
    via the ``secure_group_filters`` hook.  This model stores a ContentType + object_id
    pair so that any filter object can be referenced without a hard import.
    """

    class Meta:
        verbose_name = _("Smart Filter Binding")
        verbose_name_plural = _("Smart Filter Catalog")
        default_permissions = []

    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, editable=False, related_name="pipeline_checkfilter_set"
    )
    object_id = models.PositiveIntegerField(editable=False)
    filter_object = GenericForeignKey("content_type", "object_id")

    def __str__(self) -> str:
        try:
            return f"{self.filter_object.name}: {self.filter_object.description}"
        except Exception:
            return (
                f"Error: {self.content_type.app_label}:{self.content_type} "
                f"{self.object_id} Not Found"
            )

    def evaluate(self, user: User) -> bool:
        """Return True if this filter passes for *user*."""
        obj = self.filter_object
        if obj is None:
            logger.warning(
                "CheckFilter pk=%s has an orphaned object — treating as incomplete",
                self.pk,
            )
            return False
        try:
            return bool(obj.process_filter(user))
        except Exception:
            logger.exception(
                "process_filter raised for CheckFilter pk=%s, user %s",
                self.pk,
                user.pk,
            )
            return False

    def audit(self, user: User):
        """Return per-user audit detail dict (may be richer than a simple bool)."""
        obj = self.filter_object
        if obj is None:
            return False
        try:
            result = obj.audit_filter(User.objects.filter(pk=user.pk))
            return result.get(user.pk, False)
        except Exception:
            logger.exception(
                "audit_filter raised for CheckFilter pk=%s, user %s",
                self.pk,
                user.pk,
            )
            return False


# ---------------------------------------------------------------------------
# Flow enumerations
# ---------------------------------------------------------------------------


class FlowType(models.TextChoices):
    ONBOARDING = "onboarding", _("Onboarding")
    TRAINING = "training", _("Training")
    CERTIFICATION = "certification", _("Certification")
    VETTING = "vetting", _("Vetting")
    INDUSTRY = "industry", _("Industry")
    OTHER = "other", _("Other")


class FlowStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    PUBLISHED = "published", _("Published")
    ARCHIVED = "archived", _("Archived")


class StepType(models.TextChoices):
    FILTER_CHECK = "filter_check", _("Smart Filter Check")
    ACKNOWLEDGEMENT = "acknowledgement", _("Acknowledgement")
    SERVICE_CHECK = "service_check", _("Service Account Check")


class AssignmentStatus(models.TextChoices):
    ASSIGNED = "assigned", _("Assigned")
    IN_PROGRESS = "in_progress", _("In Progress")
    COMPLETED = "completed", _("Completed")


# ---------------------------------------------------------------------------
# OnboardingFlow
# ---------------------------------------------------------------------------


class OnboardingFlow(models.Model):
    """
    A named, typed flow that guides users through a structured sequence of steps.

    Visibility is controlled via M2M relationships to States, Groups, Corporations,
    Alliances, Factions, and Characters — exactly matching the existing Wizard model.
    Flows with ``auto_assign=True`` are automatically assigned to eligible users when
    their profile changes.

    Only flows with ``status=published`` are visible to end-users.  Admins may preview
    draft flows via a direct URL.
    """

    objects = FlowManager()

    name = models.CharField(_("name"), max_length=100)
    slug = models.SlugField(
        _("slug"),
        unique=True,
        help_text=_(
            "URL-friendly identifier used in permalinks.  "
            "Auto-generated from the name if left blank."
        ),
    )
    description = models.TextField(
        _("description"),
        blank=True,
        help_text=_("Short summary shown on the index and dashboard."),
    )
    body_complete = models.TextField(
        _("completion message"),
        blank=True,
        help_text=_(
            "Markdown body shown when the user has completed every required step.  "
            "Supports {{ user }} template variable."
        ),
    )
    flow_type = models.CharField(
        _("flow type"),
        max_length=20,
        choices=FlowType.choices,
        default=FlowType.ONBOARDING,
    )
    status = models.CharField(
        _("status"),
        max_length=10,
        choices=FlowStatus.choices,
        default=FlowStatus.DRAFT,
    )
    auto_assign = models.BooleanField(
        _("auto assign"),
        default=False,
        help_text=_(
            "Automatically assign this flow to users who meet the visibility "
            "requirements when their profile is updated."
        ),
    )

    # ---- Visibility targeting ------------------------------------------------

    states = models.ManyToManyField(
        State,
        blank=True,
        verbose_name=_("states"),
        related_name="pipeline_flows",
    )
    groups = models.ManyToManyField(
        Group,
        blank=True,
        verbose_name=_("groups"),
        related_name="pipeline_flows",
    )
    corporations = models.ManyToManyField(
        EveCorporationInfo,
        blank=True,
        verbose_name=_("corporations"),
        related_name="pipeline_flows",
    )
    alliances = models.ManyToManyField(
        EveAllianceInfo,
        blank=True,
        verbose_name=_("alliances"),
        related_name="pipeline_flows",
    )
    factions = models.ManyToManyField(
        EveFactionInfo,
        blank=True,
        verbose_name=_("factions"),
        related_name="pipeline_flows",
    )
    characters = models.ManyToManyField(
        EveCharacter,
        blank=True,
        verbose_name=_("characters"),
        related_name="pipeline_flows",
    )

    # ---- On-complete automation (Phase 4 stubs — stored now, used later) -----

    on_complete_add_groups = models.ManyToManyField(
        Group,
        blank=True,
        verbose_name=_("on-complete: add to groups"),
        related_name="pipeline_flows_on_complete",
        help_text=_("Groups to automatically add the user to when this flow is completed."),
    )
    on_complete_webhook_url = models.URLField(
        _("on-complete: webhook URL"),
        blank=True,
        help_text=_(
            "POST to this URL (JSON body: {user_id, username, flow_id, flow_name}) "
            "when a user completes this flow."
        ),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("flow")
        verbose_name_plural = _("flows")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    # ---- Helpers -------------------------------------------------------------

    @property
    def is_published(self) -> bool:
        return self.status == FlowStatus.PUBLISHED

    @property
    def has_visibility_configured(self) -> bool:
        return (
            self.states.exists()
            or self.groups.exists()
            or self.corporations.exists()
            or self.alliances.exists()
            or self.factions.exists()
            or self.characters.exists()
        )

    def is_visible_to_user(self, user: User) -> bool:
        """
        Return True if *user* meets at least one of this flow's visibility criteria.

        A flow with no visibility configured is not visible to anyone — admins must
        explicitly choose an audience before publishing.
        """
        if not self.has_visibility_configured:
            return False

        profile = user.profile
        if self.states.filter(pk=profile.state_id).exists():
            return True
        if self.groups.filter(pk__in=user.groups.values_list("pk", flat=True)).exists():
            return True

        char_qs = user.character_ownerships.select_related("character")
        corp_ids = char_qs.values_list("character__corporation_id", flat=True)
        alliance_ids = char_qs.exclude(character__alliance_id=None).values_list(
            "character__alliance_id", flat=True
        )
        char_ids = char_qs.values_list("character__character_id", flat=True)
        faction_ids = char_qs.exclude(character__faction_id=None).values_list(
            "character__faction_id", flat=True
        )

        if self.corporations.filter(corporation_id__in=corp_ids).exists():
            return True
        if self.alliances.filter(alliance_id__in=alliance_ids).exists():
            return True
        if self.characters.filter(character_id__in=char_ids).exists():
            return True
        if self.factions.filter(faction_id__in=faction_ids).exists():
            return True

        return False

    def get_step_count(self) -> int:
        return self.steps.count()

    def get_completion_pct(self, user: User, assignment: "FlowAssignment") -> float:
        """Overall completion percentage (0.0–1.0) for *user* on *assignment*."""
        steps = list(self.steps.all())
        if not steps:
            return 1.0
        completed = sum(1 for s in steps if s.is_complete(user, assignment))
        return completed / len(steps)

    def is_complete(self, user: User, assignment: "FlowAssignment") -> bool:
        """True when all *required* steps are complete."""
        return all(
            s.is_complete(user, assignment)
            for s in self.steps.all()
            if not s.optional
        )


# ---------------------------------------------------------------------------
# FlowStep
# ---------------------------------------------------------------------------


class FlowStep(models.Model):
    """
    A single ordered step within an OnboardingFlow.

    Three step types are supported in Phase 1:

    ``filter_check``
        Completion is determined automatically by evaluating one or more Smart
        Filters.  The user cannot manually mark this step complete.

    ``acknowledgement``
        The user reads the step body and clicks a confirmation button.  Stored
        as a StepCompletion record.

    ``service_check``
        Checks whether the user has an active account in an installed AA service
        (Discord, Mumble, TeamSpeak, …) via the service registry.  If the
        service is not installed and ``service_fallback_acknowledgement`` is
        True, the step falls back to acknowledgement mode.
    """

    flow = models.ForeignKey(
        OnboardingFlow,
        on_delete=models.CASCADE,
        related_name="steps",
        verbose_name=_("flow"),
    )
    order = models.PositiveIntegerField(_("order"), default=0, db_index=True)
    name = models.CharField(_("name"), max_length=100)
    description = models.CharField(
        _("description"),
        max_length=500,
        blank=True,
        help_text=_("Short summary shown in the step sidebar."),
    )
    body = models.TextField(
        _("body"),
        blank=True,
        help_text=_(
            "Main body shown to the user.  Supports Markdown if the 'markdown' "
            "package is installed, otherwise rendered as plain text with line breaks."
        ),
    )
    step_type = models.CharField(
        _("step type"),
        max_length=20,
        choices=StepType.choices,
        default=StepType.FILTER_CHECK,
    )
    optional = models.BooleanField(
        _("optional"),
        default=False,
        help_text=_(
            "Optional steps show progress credit but do not block flow completion."
        ),
    )

    # ---- Service-check specific fields ---------------------------------------

    service_slug = models.CharField(
        _("service slug"),
        max_length=50,
        blank=True,
        help_text=_(
            "Service identifier for 'Service Account Check' steps.  "
            "Known values: discord, mumble, teamspeak.  "
            "Leave blank for other step types."
        ),
    )
    service_fallback_acknowledgement = models.BooleanField(
        _("fall back to acknowledgement if service not installed"),
        default=True,
        help_text=_(
            "When the specified service is not installed, convert this step to "
            "an acknowledgement instead of auto-passing it."
        ),
    )

    class Meta:
        verbose_name = _("flow step")
        verbose_name_plural = _("flow steps")
        ordering = ["order"]

    def __str__(self) -> str:
        return f"{self.flow.name} › {self.name}"

    # ---- Completion logic ----------------------------------------------------

    @functools.cached_property
    def effective_type(self) -> str:
        """
        Return the type that should be used for rendering and completion checks.

        For ``service_check`` steps, this may differ from ``step_type`` when the
        target service is not installed.  Result is cached on the instance for the
        lifetime of the object (one HTTP request cycle).
        """
        if self.step_type != StepType.SERVICE_CHECK:
            return self.step_type

        from .service_registry import is_service_installed

        if not is_service_installed(self.service_slug):
            if self.service_fallback_acknowledgement:
                return StepType.ACKNOWLEDGEMENT
            return "auto_pass"

        return StepType.SERVICE_CHECK

    def is_complete(self, user: User, assignment: "FlowAssignment") -> bool:
        etype = self.effective_type

        if etype == StepType.FILTER_CHECK:
            checks = list(self.checks.select_related("filter__content_type").all())
            if not checks:
                return True
            return all(c.filter.evaluate(user) for c in checks)

        if etype in (StepType.ACKNOWLEDGEMENT, "auto_pass"):
            if etype == "auto_pass":
                return True
            return StepCompletion.objects.filter(assignment=assignment, step=self).exists()

        if etype == StepType.SERVICE_CHECK:
            from .service_registry import check_service_for_user

            return check_service_for_user(self.service_slug, user)

        return False

    def get_completion_pct(self, user: User, assignment: "FlowAssignment") -> float:
        etype = self.effective_type
        if etype == StepType.FILTER_CHECK:
            checks = list(self.checks.select_related("filter__content_type").all())
            if not checks:
                return 1.0
            passed = sum(1 for c in checks if c.filter.evaluate(user))
            return passed / len(checks)
        return 1.0 if self.is_complete(user, assignment) else 0.0

    def get_check_details(self, user: User) -> list:
        """Return a list of dicts for each StepCheck with pass/fail state."""
        if self.step_type != StepType.FILTER_CHECK:
            return []
        return [
            {
                "check": sc,
                "label": sc.label or str(sc.filter),
                "passed": sc.filter.evaluate(user),
            }
            for sc in self.checks.select_related(
                "filter__content_type"
            ).order_by("order")
        ]


# ---------------------------------------------------------------------------
# StepCheck
# ---------------------------------------------------------------------------


class StepCheck(models.Model):
    """
    Binds a Smart Filter to a ``filter_check`` FlowStep.

    Multiple checks can be attached to a single step; all must pass.
    """

    step = models.ForeignKey(
        FlowStep,
        on_delete=models.CASCADE,
        related_name="checks",
        verbose_name=_("step"),
    )
    order = models.PositiveIntegerField(_("order"), default=0)
    filter = models.ForeignKey(
        CheckFilter,
        on_delete=models.CASCADE,
        verbose_name=_("smart filter"),
    )
    label = models.CharField(
        _("label"),
        max_length=255,
        blank=True,
        help_text=_("Custom label shown to users.  Defaults to the filter name if blank."),
    )

    class Meta:
        verbose_name = _("step check")
        verbose_name_plural = _("step checks")
        ordering = ["order"]

    def __str__(self) -> str:
        return self.label or str(self.filter)


# ---------------------------------------------------------------------------
# FlowAssignment
# ---------------------------------------------------------------------------


class FlowAssignment(models.Model):
    """
    Records that a specific user has been assigned a specific flow.

    This is the primary state carrier.  ``status`` progresses from ``assigned``
    → ``in_progress`` → ``completed``.  The status is authoritative; it must be
    recalculated whenever a step completion changes.
    """

    flow = models.ForeignKey(
        OnboardingFlow,
        on_delete=models.CASCADE,
        related_name="assignments",
        verbose_name=_("flow"),
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="pipeline_assignments",
        verbose_name=_("user"),
    )
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=AssignmentStatus.choices,
        default=AssignmentStatus.ASSIGNED,
        db_index=True,
    )
    assigned_at = models.DateTimeField(_("assigned at"), auto_now_add=True)
    completed_at = models.DateTimeField(_("completed at"), null=True, blank=True)

    class Meta:
        verbose_name = _("assignment")
        verbose_name_plural = _("assignments")
        constraints = [
            models.UniqueConstraint(
                fields=["flow", "user"],
                name="pipeline_flowassignment_flow_user_unique",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user.username} → {self.flow.name} ({self.get_status_display()})"

    def recalculate_status(self) -> None:
        """
        Recompute and persist status based on live step completion state.

        Call this after any step completion is created or deleted.
        """
        if self.flow.is_complete(self.user, self):
            self._mark_complete()
        elif self.step_completions.exists():
            if self.status == AssignmentStatus.ASSIGNED:
                self.status = AssignmentStatus.IN_PROGRESS
                self.save(update_fields=["status"])
        # If no completions, status stays ASSIGNED.

    def _mark_complete(self) -> None:
        if self.status != AssignmentStatus.COMPLETED:
            self.status = AssignmentStatus.COMPLETED
            self.completed_at = timezone.now()
            self.save(update_fields=["status", "completed_at"])
            self._stamp_all_step_completions()
            self._fire_on_complete_actions()

    def _stamp_all_step_completions(self) -> None:
        """
        Ensure a StepCompletion record exists for every completed step.

        Acknowledgement steps already create their own records when the user
        clicks confirm.  This method fills in filter_check and service_check
        steps (which are evaluated dynamically and never self-record) so that
        the admin Step Completions list reflects every step in the flow.
        """
        existing_ids = set(
            self.step_completions.values_list("step_id", flat=True)
        )
        to_create = [
            StepCompletion(
                assignment=self,
                step=step,
                completed_by=self.user,
                metadata={"auto_recorded": True, "step_type": step.step_type},
            )
            for step in self.flow.steps.all()
            if step.pk not in existing_ids and step.is_complete(self.user, self)
        ]
        if to_create:
            StepCompletion.objects.bulk_create(to_create, ignore_conflicts=True)

    def _fire_on_complete_actions(self) -> None:
        """Execute any on-complete automation configured on the flow."""
        flow = self.flow

        # Add user to on-complete groups
        groups_to_add = list(flow.on_complete_add_groups.all())
        if groups_to_add:
            self.user.groups.add(*groups_to_add)
            logger.info(
                "Pipeline: added user %s to groups %s after completing flow %s",
                self.user_id,
                [g.pk for g in groups_to_add],
                flow.pk,
            )

        # Fire generic completion webhook
        if flow.on_complete_webhook_url:
            from .tasks import fire_completion_webhook
            fire_completion_webhook.delay(self.pk)

        # Fire Discord completion notifications
        if flow.discord_webhooks.filter(enabled=True).exists():
            from .tasks import fire_discord_completion_notification
            fire_discord_completion_notification.delay(self.pk)


# ---------------------------------------------------------------------------
# StepCompletion
# ---------------------------------------------------------------------------


class StepCompletion(models.Model):
    """
    Records that a user completed a self-guided step (acknowledgement or service_check
    fallback).  Filter-check steps are never stored here — their completion state is
    always derived live from Smart Filters.
    """

    assignment = models.ForeignKey(
        FlowAssignment,
        on_delete=models.CASCADE,
        related_name="step_completions",
        verbose_name=_("assignment"),
    )
    step = models.ForeignKey(
        FlowStep,
        on_delete=models.CASCADE,
        verbose_name=_("step"),
    )
    completed_at = models.DateTimeField(_("completed at"), auto_now_add=True)
    completed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("completed by"),
        help_text=_("Set to the approving admin for manual_approval steps (Phase 5)."),
    )
    metadata = models.JSONField(
        _("metadata"),
        default=dict,
        blank=True,
        help_text=_("Arbitrary JSON — stores acknowledgement snapshots, form data, etc."),
    )

    class Meta:
        verbose_name = _("step completion")
        verbose_name_plural = _("step completions")
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "step"],
                name="pipeline_stepcompletion_assignment_step_unique",
            )
        ]

    def __str__(self) -> str:
        return f"{self.assignment.user.username}: {self.step.name}"


# ---------------------------------------------------------------------------
# FlowDiscordWebhook
# ---------------------------------------------------------------------------


class FlowDiscordWebhook(models.Model):
    """
    Discord incoming webhook that fires when a user completes this flow.

    Attach one or more webhooks per flow so that different channels (e.g. a
    general onboarding channel and a leadership channel) can each be notified.
    A formatted embed is POSTed to each enabled webhook URL.
    """

    flow = models.ForeignKey(
        OnboardingFlow,
        on_delete=models.CASCADE,
        related_name="discord_webhooks",
        verbose_name=_("flow"),
    )
    webhook_url = models.URLField(
        _("Discord webhook URL"),
        help_text=_(
            "Paste the Discord channel webhook URL "
            "(Server Settings → Integrations → Webhooks)."
        ),
    )
    message = models.CharField(
        _("message prefix"),
        max_length=1000,
        blank=True,
        help_text=_(
            "Optional plain-text message posted above the embed.  "
            "Supports {username} and {flow_name} placeholders."
        ),
    )
    enabled = models.BooleanField(_("enabled"), default=True)

    class Meta:
        verbose_name = _("Discord completion webhook")
        verbose_name_plural = _("Discord completion webhooks")
        default_permissions = []

    def __str__(self) -> str:
        truncated = self.webhook_url[:50]
        if len(self.webhook_url) > 50:
            truncated += "…"
        return f"{self.flow.name} → {truncated}"
