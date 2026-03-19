"""
Pipeline — GDPR personal-data hook for aa-gdpr.

Registers with the allianceauth hooks system so that aa-gdpr can export and
delete personal data held by this app on a per-user basis.

This module is imported by auth_hooks.py.  If aa-gdpr is not installed the
hook registration is silently ignored by the Alliance Auth hooks framework.

aa-gdpr hook interface (as used by the broader AA ecosystem):
    class must expose:
        app_name (str)       — human-readable app label
        get_personal_data(user) → dict|list   — data for export
        delete_personal_data(user)            — hard-delete personal data

The dict returned by get_personal_data is serialised as JSON and offered to
the user as a download.  Keep the structure stable across versions; add new
keys rather than renaming or removing existing ones.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


class PipelineGDPRHook:
    """
    GDPR personal-data processor for the Pipeline app.

    Exports:
    - All FlowAssignment records for the user (flow name, status, dates).
    - All StepCompletion records linked to those assignments (step name, date,
      metadata snapshot).

    Deletion:
    - Deletes all FlowAssignment records for the user.  StepCompletion records
      cascade automatically (ON DELETE CASCADE via FK).
    """

    app_name = "Pipeline"

    # ── aa-gdpr may call either spelling depending on version ────────────────
    def get_personal_data(self, user: User) -> dict:
        return self._build_export(user)

    def get_personal_data_for(self, user: User) -> dict:
        return self._build_export(user)

    def delete_personal_data(self, user: User) -> None:
        self._hard_delete(user)

    def delete_personal_data_for(self, user: User) -> None:
        self._hard_delete(user)

    # ── Implementation ───────────────────────────────────────────────────────

    def _build_export(self, user: User) -> dict:
        """Return a serialisation-ready dict of all personal data for *user*."""
        from .models import FlowAssignment

        assignments = (
            FlowAssignment.objects.filter(user=user)
            .select_related("flow")
            .prefetch_related("step_completions__step")
            .order_by("flow__name")
        )

        assignment_list = []
        for a in assignments:
            completions = []
            for sc in a.step_completions.all():
                completions.append(
                    {
                        "step_name": sc.step.name,
                        "step_type": sc.step.step_type,
                        "completed_at": sc.completed_at.isoformat() if sc.completed_at else None,
                        "metadata": sc.metadata,
                    }
                )

            assignment_list.append(
                {
                    "flow_name": a.flow.name,
                    "flow_type": a.flow.flow_type,
                    "status": a.status,
                    "assigned_at": a.assigned_at.isoformat() if a.assigned_at else None,
                    "completed_at": a.completed_at.isoformat() if a.completed_at else None,
                    "step_completions": completions,
                }
            )

        return {
            "app": self.app_name,
            "user": user.username,
            "assignments": assignment_list,
        }

    def _hard_delete(self, user: User) -> None:
        """
        Hard-delete all personal data for *user*.

        FlowAssignment → StepCompletion cascade via Django FK, so deleting
        assignments is sufficient.
        """
        from .models import FlowAssignment

        deleted_count, _ = FlowAssignment.objects.filter(user=user).delete()
        logger.info(
            "Pipeline GDPR: deleted %d assignment(s) for user %s (pk=%s)",
            deleted_count,
            user.username,
            user.pk,
        )
