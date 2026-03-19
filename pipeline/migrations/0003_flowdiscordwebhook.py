from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("pipeline", "0002_checkfilter_content_type_related_name"),
    ]

    operations = [
        migrations.CreateModel(
            name="FlowDiscordWebhook",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "webhook_url",
                    models.URLField(
                        help_text="Paste the Discord channel webhook URL (Server Settings → Integrations → Webhooks).",
                        verbose_name="Discord webhook URL",
                    ),
                ),
                (
                    "message",
                    models.CharField(
                        blank=True,
                        help_text="Optional plain-text message posted above the embed.  Supports {username} and {flow_name} placeholders.",
                        max_length=1000,
                        verbose_name="message prefix",
                    ),
                ),
                ("enabled", models.BooleanField(default=True, verbose_name="enabled")),
                (
                    "flow",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="discord_webhooks",
                        to="pipeline.onboardingflow",
                        verbose_name="flow",
                    ),
                ),
            ],
            options={
                "verbose_name": "Discord completion webhook",
                "verbose_name_plural": "Discord completion webhooks",
                "default_permissions": [],
            },
        ),
    ]
