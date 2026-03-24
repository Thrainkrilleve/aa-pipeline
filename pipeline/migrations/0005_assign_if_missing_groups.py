"""
Migration 0005 — add assign_if_missing_groups M2M to OnboardingFlow.

Enables negative-targeting auto-assignment: flows can now be automatically
assigned to any user who does NOT yet belong to a specified set of groups.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("pipeline", "0004_add_manage_flows_permission"),
    ]

    operations = [
        migrations.AddField(
            model_name="onboardingflow",
            name="assign_if_missing_groups",
            field=models.ManyToManyField(
                blank=True,
                help_text=(
                    "Automatically assign this flow to any user who does NOT belong "
                    "to any of these groups.  When the user gains one of these groups "
                    "their unstarted assignment is automatically removed."
                ),
                related_name="pipeline_flows_missing_trigger",
                to="auth.group",
                verbose_name="assign if missing groups",
            ),
        ),
    ]
