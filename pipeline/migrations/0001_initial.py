# Generated migration for aa-pipeline 0.1.0

# Django
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("authentication", "0024_alter_userprofile_language"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("eveonline", "0017_alliance_and_corp_names_are_not_unique"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # --- General (permissions only, unmanaged) --------------------------
        migrations.CreateModel(
            name="General",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
            ],
            options={
                "permissions": (("basic_access", "Can access this app"),),
                "managed": False,
                "default_permissions": (),
            },
        ),
        # --- CheckFilter ----------------------------------------------------
        migrations.CreateModel(
            name="CheckFilter",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "object_id",
                    models.PositiveIntegerField(editable=False),
                ),
                (
                    "content_type",
                    models.ForeignKey(
                        editable=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="contenttypes.contenttype",
                    ),
                ),
            ],
            options={
                "verbose_name": "Smart Filter Binding",
                "verbose_name_plural": "Smart Filter Catalog",
                "default_permissions": [],
            },
        ),
        # --- OnboardingFlow -------------------------------------------------
        migrations.CreateModel(
            name="OnboardingFlow",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100, verbose_name="name")),
                (
                    "slug",
                    models.SlugField(
                        unique=True,
                        help_text=(
                            "URL-friendly identifier used in permalinks.  "
                            "Auto-generated from the name if left blank."
                        ),
                        verbose_name="slug",
                    ),
                ),
                (
                    "description",
                    models.TextField(blank=True, verbose_name="description"),
                ),
                (
                    "body_complete",
                    models.TextField(
                        blank=True,
                        help_text=(
                            "Markdown body shown when the user has completed every "
                            "required step.  Supports {{ user }} template variable."
                        ),
                        verbose_name="completion message",
                    ),
                ),
                (
                    "flow_type",
                    models.CharField(
                        choices=[
                            ("onboarding", "Onboarding"),
                            ("training", "Training"),
                            ("certification", "Certification"),
                            ("vetting", "Vetting"),
                            ("industry", "Industry"),
                            ("other", "Other"),
                        ],
                        default="onboarding",
                        max_length=20,
                        verbose_name="flow type",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("published", "Published"),
                            ("archived", "Archived"),
                        ],
                        default="draft",
                        max_length=10,
                        verbose_name="status",
                    ),
                ),
                (
                    "auto_assign",
                    models.BooleanField(
                        default=False,
                        help_text=(
                            "Automatically assign this flow to users who meet the "
                            "visibility requirements when their profile is updated."
                        ),
                        verbose_name="auto assign",
                    ),
                ),
                (
                    "on_complete_webhook_url",
                    models.URLField(
                        blank=True,
                        help_text=(
                            "POST to this URL (JSON body: {user_id, username, "
                            "flow_id, flow_name}) when a user completes this flow."
                        ),
                        verbose_name="on-complete: webhook URL",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                # Visibility M2M
                (
                    "alliances",
                    models.ManyToManyField(
                        blank=True,
                        related_name="pipeline_flows",
                        to="eveonline.eveallianceinfo",
                        verbose_name="alliances",
                    ),
                ),
                (
                    "characters",
                    models.ManyToManyField(
                        blank=True,
                        related_name="pipeline_flows",
                        to="eveonline.evecharacter",
                        verbose_name="characters",
                    ),
                ),
                (
                    "corporations",
                    models.ManyToManyField(
                        blank=True,
                        related_name="pipeline_flows",
                        to="eveonline.evecorporationinfo",
                        verbose_name="corporations",
                    ),
                ),
                (
                    "factions",
                    models.ManyToManyField(
                        blank=True,
                        related_name="pipeline_flows",
                        to="eveonline.evefactioninfo",
                        verbose_name="factions",
                    ),
                ),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        related_name="pipeline_flows",
                        to="auth.group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "on_complete_add_groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text=(
                            "Groups to automatically add the user to when this flow is completed."
                        ),
                        related_name="pipeline_flows_on_complete",
                        to="auth.group",
                        verbose_name="on-complete: add to groups",
                    ),
                ),
                (
                    "states",
                    models.ManyToManyField(
                        blank=True,
                        related_name="pipeline_flows",
                        to="authentication.state",
                        verbose_name="states",
                    ),
                ),
            ],
            options={
                "verbose_name": "flow",
                "verbose_name_plural": "flows",
                "ordering": ["name"],
            },
        ),
        # --- FlowStep -------------------------------------------------------
        migrations.CreateModel(
            name="FlowStep",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "order",
                    models.PositiveIntegerField(
                        db_index=True, default=0, verbose_name="order"
                    ),
                ),
                (
                    "name",
                    models.CharField(max_length=100, verbose_name="name"),
                ),
                (
                    "description",
                    models.CharField(
                        blank=True,
                        max_length=500,
                        help_text="Short summary shown in the step sidebar.",
                        verbose_name="description",
                    ),
                ),
                (
                    "body",
                    models.TextField(
                        blank=True,
                        help_text=(
                            "Main body shown to the user.  Supports Markdown if the "
                            "'markdown' package is installed."
                        ),
                        verbose_name="body",
                    ),
                ),
                (
                    "step_type",
                    models.CharField(
                        choices=[
                            ("filter_check", "Smart Filter Check"),
                            ("acknowledgement", "Acknowledgement"),
                            ("service_check", "Service Account Check"),
                        ],
                        default="filter_check",
                        max_length=20,
                        verbose_name="step type",
                    ),
                ),
                (
                    "optional",
                    models.BooleanField(
                        default=False,
                        help_text=(
                            "Optional steps show progress credit but do not block "
                            "flow completion."
                        ),
                        verbose_name="optional",
                    ),
                ),
                (
                    "service_slug",
                    models.CharField(
                        blank=True,
                        max_length=50,
                        help_text=(
                            "Service identifier for 'Service Account Check' steps.  "
                            "Known values: discord, mumble, teamspeak."
                        ),
                        verbose_name="service slug",
                    ),
                ),
                (
                    "service_fallback_acknowledgement",
                    models.BooleanField(
                        default=True,
                        help_text=(
                            "When the specified service is not installed, convert this "
                            "step to an acknowledgement instead of auto-passing it."
                        ),
                        verbose_name="fall back to acknowledgement if service not installed",
                    ),
                ),
                (
                    "flow",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="steps",
                        to="pipeline.onboardingflow",
                        verbose_name="flow",
                    ),
                ),
            ],
            options={
                "verbose_name": "flow step",
                "verbose_name_plural": "flow steps",
                "ordering": ["order"],
            },
        ),
        # --- StepCheck ------------------------------------------------------
        migrations.CreateModel(
            name="StepCheck",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "order",
                    models.PositiveIntegerField(default=0, verbose_name="order"),
                ),
                (
                    "label",
                    models.CharField(
                        blank=True,
                        max_length=255,
                        help_text="Custom label shown to users.  Defaults to the filter name if blank.",
                        verbose_name="label",
                    ),
                ),
                (
                    "filter",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="pipeline.checkfilter",
                        verbose_name="smart filter",
                    ),
                ),
                (
                    "step",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="checks",
                        to="pipeline.flowstep",
                        verbose_name="step",
                    ),
                ),
            ],
            options={
                "verbose_name": "step check",
                "verbose_name_plural": "step checks",
                "ordering": ["order"],
            },
        ),
        # --- FlowAssignment -------------------------------------------------
        migrations.CreateModel(
            name="FlowAssignment",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("assigned", "Assigned"),
                            ("in_progress", "In Progress"),
                            ("completed", "Completed"),
                        ],
                        db_index=True,
                        default="assigned",
                        max_length=20,
                        verbose_name="status",
                    ),
                ),
                (
                    "assigned_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="assigned at"),
                ),
                (
                    "completed_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="completed at"
                    ),
                ),
                (
                    "flow",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assignments",
                        to="pipeline.onboardingflow",
                        verbose_name="flow",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pipeline_assignments",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="user",
                    ),
                ),
            ],
            options={
                "verbose_name": "assignment",
                "verbose_name_plural": "assignments",
            },
        ),
        migrations.AddConstraint(
            model_name="flowassignment",
            constraint=models.UniqueConstraint(
                fields=("flow", "user"),
                name="pipeline_flowassignment_flow_user_unique",
            ),
        ),
        # --- StepCompletion -------------------------------------------------
        migrations.CreateModel(
            name="StepCompletion",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "completed_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="completed at"
                    ),
                ),
                (
                    "metadata",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text=(
                            "Arbitrary JSON — stores acknowledgement snapshots, "
                            "form data, etc."
                        ),
                        verbose_name="metadata",
                    ),
                ),
                (
                    "assignment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="step_completions",
                        to="pipeline.flowassignment",
                        verbose_name="assignment",
                    ),
                ),
                (
                    "completed_by",
                    models.ForeignKey(
                        blank=True,
                        help_text=(
                            "Set to the approving admin for manual_approval steps (Phase 5)."
                        ),
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="completed by",
                    ),
                ),
                (
                    "step",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="pipeline.flowstep",
                        verbose_name="step",
                    ),
                ),
            ],
            options={
                "verbose_name": "step completion",
                "verbose_name_plural": "step completions",
            },
        ),
        migrations.AddConstraint(
            model_name="stepcompletion",
            constraint=models.UniqueConstraint(
                fields=("assignment", "step"),
                name="pipeline_stepcompletion_assignment_step_unique",
            ),
        ),
    ]
