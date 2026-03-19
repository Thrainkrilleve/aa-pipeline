"""
Pipeline Celery Tasks
"""

# Standard Library
import hashlib
import hmac
import json
import logging
import urllib.error
import urllib.request

# Third Party
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_autoassign_for_user(self, user_pk: int) -> None:
    """
    Auto-assign any eligible published flows to *user_pk* and clean up flows
    the user is no longer eligible for (if not yet started).
    """
    from django.contrib.auth.models import User

    from .models import AssignmentStatus, FlowAssignment, OnboardingFlow

    try:
        user = User.objects.select_related("profile").get(pk=user_pk)
    except User.DoesNotExist:
        logger.warning("Pipeline autoassign: user pk=%s not found, skipping", user_pk)
        return

    # --- Remove assignments for flows user no longer qualifies for (ASSIGNED only) ---
    stale = FlowAssignment.objects.filter(
        user=user, status=AssignmentStatus.ASSIGNED
    ).select_related("flow")

    for assignment in stale:
        flow = assignment.flow
        if not flow.is_visible_to_user(user) and not flow.has_visibility_configured:
            continue
        if not flow.is_visible_to_user(user):
            assignment.delete()
            logger.info(
                "Pipeline: removed stale assignment for user %s, flow %s",
                user_pk,
                flow.pk,
            )

    # --- Create assignments for newly eligible auto-assign flows ---
    auto_flows = OnboardingFlow.objects.get_auto_assignable_for_user(user)
    for flow in auto_flows:
        assignment, created = FlowAssignment.objects.get_or_create(
            flow=flow,
            user=user,
            defaults={"status": AssignmentStatus.ASSIGNED},
        )
        if created:
            logger.info(
                "Pipeline: auto-assigned flow %s to user %s",
                flow.pk,
                user_pk,
            )
            _notify_user_of_assignment(user, flow)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def fire_completion_webhook(self, assignment_pk: int) -> None:
    """
    POST a JSON payload to the flow's on_complete_webhook_url.

    This task is a Phase 4 stub.  In Phase 1 it logs the intent but does not
    make the actual HTTP request (to avoid adding a hard dependency on
    ``requests`` or similar).
    """
    from .models import FlowAssignment

    try:
        assignment = FlowAssignment.objects.select_related(
            "flow", "user"
        ).get(pk=assignment_pk)
    except FlowAssignment.DoesNotExist:
        return

    url = assignment.flow.on_complete_webhook_url
    if not url:
        return

    payload = {
        "user_id": assignment.user_id,
        "username": assignment.user.username,
        "flow_id": assignment.flow_id,
        "flow_name": assignment.flow.name,
        "flow_slug": assignment.flow.slug,
        "completed_at": assignment.completed_at.isoformat() if assignment.completed_at else None,
    }
    body = json.dumps(payload).encode("utf-8")

    # HMAC-SHA256 signature using the webhook URL itself as the secret key.
    # Receivers can verify: hmac.compare_digest(expected_sig, request.headers["X-Pipeline-Signature"])
    secret = url.encode("utf-8")
    signature = hmac.new(secret, body, hashlib.sha256).hexdigest()

    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Pipeline-Signature": f"sha256={signature}",
            "User-Agent": "aa-pipeline-webhook/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            logger.info(
                "Pipeline webhook: POST to %s returned HTTP %s for assignment pk=%s",
                url,
                resp.status,
                assignment_pk,
            )
    except urllib.error.HTTPError as exc:
        logger.warning(
            "Pipeline webhook: HTTP %s from %s for assignment pk=%s — retrying",
            exc.code,
            url,
            assignment_pk,
        )
        raise self.retry(exc=exc)
    except Exception as exc:
        logger.exception(
            "Pipeline webhook: error POSTing to %s for assignment pk=%s",
            url,
            assignment_pk,
        )
        raise self.retry(exc=exc)


def _notify_user_of_assignment(user, flow) -> None:
    """Send an in-app notification when a flow is auto-assigned to a user."""
    try:
        from allianceauth.notifications import notify

        notify(
            user=user,
            title=f"New flow assigned: {flow.name}",
            message=(
                f"You have been assigned the '{flow.name}' flow. "
                f"Visit your Pipeline to get started."
            ),
            level="info",
        )
    except Exception:
        logger.exception(
            "Pipeline: failed to send assignment notification to user %s", user.pk
        )
