"""
Pipeline Signals

Handles:
  - Auto-assignment of flows when a user's profile (state / groups / character)
    changes.
  - Automatic registration of new Smart Filter objects into the CheckFilter
    catalog, mirroring the pattern used by allianceauth-secure-groups.
  - Removal of CheckFilter entries when a Smart Filter object is deleted.
"""

# Standard Library
import logging

# Django
from django.contrib.auth.models import User
from django.db.models.signals import m2m_changed, post_save, pre_delete
from django.dispatch import receiver

# Alliance Auth
from allianceauth import hooks
from allianceauth.authentication.models import CharacterOwnership, UserProfile

from . import models
from .models import FlowAssignment, OnboardingFlow

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Auto-assignment triggers
# ---------------------------------------------------------------------------


@receiver(post_save, sender=UserProfile)
def _state_changed(sender, instance: UserProfile, **kwargs) -> None:
    _enqueue_autoassign(instance.user)


@receiver(m2m_changed, sender=User.groups.through)
def _groups_changed(sender, instance, action: str, **kwargs) -> None:
    if action not in ("post_add", "post_remove", "post_clear"):
        return
    if isinstance(instance, User):
        _enqueue_autoassign(instance)


@receiver(post_save, sender=CharacterOwnership)
def _char_ownership_changed(sender, instance: CharacterOwnership, **kwargs) -> None:
    _enqueue_autoassign(instance.user)


def _enqueue_autoassign(user: User) -> None:
    """
    Queue a Celery task to handle auto-assignment logic for *user*.

    Using a task avoids blocking the request cycle and deduplicates rapid
    successive calls (e.g. bulk group changes).
    """
    try:
        from .tasks import process_autoassign_for_user

        process_autoassign_for_user.delay(user.pk)
    except Exception:
        logger.exception(
            "Pipeline: failed to enqueue autoassign task for user %s", user.pk
        )


# ---------------------------------------------------------------------------
# Smart Filter catalog maintenance
# ---------------------------------------------------------------------------


class _FilterHookCache:
    """Lazy-loaded set of Smart Filter model classes from registered hooks."""

    _hooks: set | None = None

    def get_hooks(self) -> set:
        if self._hooks is None:
            hook_set: set = set()
            for app_hook in hooks.get_hooks("secure_group_filters"):
                for filter_model in app_hook():
                    hook_set.add(filter_model)
            self._hooks = hook_set
        return self._hooks


_filter_hook_cache = _FilterHookCache()


def _register_filter(sender, instance, created: bool, **kwargs) -> None:
    """Create a CheckFilter entry when a new Smart Filter object is saved."""
    if not created:
        return
    try:
        models.CheckFilter.objects.create(filter_object=instance)
    except Exception:
        logger.exception(
            "Pipeline: failed to create CheckFilter for %s (pk=%s)",
            sender,
            instance.pk,
        )


def _deregister_filter(sender, instance, **kwargs) -> None:
    """Remove the CheckFilter entry when a Smart Filter object is deleted."""
    from django.contrib.contenttypes.models import ContentType

    try:
        ct = ContentType.objects.get_for_model(instance)
        models.CheckFilter.objects.filter(
            content_type=ct, object_id=instance.pk
        ).delete()
    except Exception:
        logger.exception(
            "Pipeline: failed to delete CheckFilter for %s (pk=%s)",
            sender,
            instance.pk,
        )


# Connect signals for every registered Smart Filter model
for _filter_model in _filter_hook_cache.get_hooks():
    post_save.connect(_register_filter, sender=_filter_model)
    pre_delete.connect(_deregister_filter, sender=_filter_model)
