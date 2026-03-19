"""
Management command: pipeline_sync_filters

Registers any Smart Filter objects that already existed when the pipeline app
was installed (or that were created without triggering the post_save signal).

Run this once after installation, or any time you add new Smart Filter types
from third-party apps.

Usage:
    auth pipeline_sync_filters
    auth pipeline_sync_filters --dry-run
"""

# Django
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _

# Alliance Auth
from allianceauth import hooks


class Command(BaseCommand):
    help = "Sync existing Smart Filter objects into the Pipeline CheckFilter catalog"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without making any changes.",
        )

    def handle(self, *args, **options):
        # Import here to avoid circular imports at module level
        from pipeline.models import CheckFilter  # noqa: PLC0415

        dry_run = options["dry_run"]

        # Collect all registered Smart Filter model classes
        filter_models = set()
        for app_hook in hooks.get_hooks("secure_group_filters"):
            for model in app_hook():
                filter_models.add(model)

        if not filter_models:
            self.stdout.write(
                self.style.WARNING(
                    "No Smart Filter models found via secure_group_filters hook.  "
                    "Is allianceauth-secure-groups (or a compatible app) installed and configured?"
                )
            )
            return

        created_count = 0
        skipped_count = 0

        for filter_model in sorted(filter_models, key=lambda m: m.__name__):
            ct = ContentType.objects.get_for_model(filter_model)
            existing_ids = set(
                CheckFilter.objects.filter(content_type=ct).values_list("object_id", flat=True)
            )

            for obj in filter_model.objects.all():
                if obj.pk in existing_ids:
                    skipped_count += 1
                    self.stdout.write(
                        f"  SKIP  {ct.app_label}.{ct.model}:{obj.pk} — already registered"
                    )
                else:
                    if not dry_run:
                        CheckFilter.objects.create(content_type=ct, object_id=obj.pk)
                    created_count += 1
                    prefix = "DRY-RUN" if dry_run else "CREATE"
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  {prefix}  {ct.app_label}.{ct.model}:{obj.pk} — {obj}"
                        )
                    )

        action = "Would create" if dry_run else "Created"
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{action} {created_count} CheckFilter entry/entries.  "
                f"Skipped {skipped_count} already-registered entry/entries."
            )
        )
