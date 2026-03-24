"""
FlowManager — queries for user-visible and user-assigned flows.

Mirrors the WizardManager from the original workflows app but updated for the
new data model (FlowAssignment instead of ActionItem, status lifecycle, and
published-only visibility for end-users).
"""

# Django
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q


class FlowManager(models.Manager):
    """Custom queryset helpers for OnboardingFlow."""

    # ------------------------------------------------------------------
    # Assignment queries
    # ------------------------------------------------------------------

    def get_assigned_for_user(self, user: User, include_completed: bool = False):
        """
        Flows that have an explicit FlowAssignment for *user*.

        By default only returns incomplete (assigned / in_progress) flows.
        Pass ``include_completed=True`` to include completed ones as well.
        """
        if include_completed:
            return self.filter(assignments__user=user).distinct()
        # Combine both conditions in a single filter() so Django generates one
        # JOIN scoped to the user's own assignment — avoids the multi-valued FK
        # pitfall where a separate exclude() would match *any* user's completed
        # assignment and incorrectly hide the flow for everyone else.
        return self.filter(
            assignments__user=user,
            assignments__status__in=["assigned", "in_progress"],
        ).distinct()

    def get_auto_assignable_for_user(self, user: User):
        """
        Published, auto-assign flows that *user* is eligible for but has not yet
        been assigned.
        """
        return (
            self.get_visible_for_user(user)
            .filter(auto_assign=True)
            .exclude(assignments__user=user)
            .distinct()
        )

    # ------------------------------------------------------------------
    # Visibility queries (published only)
    # ------------------------------------------------------------------

    def get_visible_for_user(self, user: User):
        """
        All *published* flows that *user* is eligible to see, based on their
        state, groups, corporation, alliance, faction, or character (positive
        targeting), or because they are missing a specific group (negative
        targeting via ``assign_if_missing_groups``).
        """
        profile = user.profile

        char_qs = user.character_ownerships.select_related("character")
        corp_ids = char_qs.values_list("character__corporation_id", flat=True)
        alliance_ids = char_qs.exclude(character__alliance_id=None).values_list(
            "character__alliance_id", flat=True
        )
        char_ids = char_qs.values_list("character__character_id", flat=True)
        faction_ids = char_qs.exclude(character__faction_id=None).values_list(
            "character__faction_id", flat=True
        )

        # Positive targeting: user matches at least one configured criterion
        positive_qs = (
            self.filter(status="published")
            .filter(
                Q(states=profile.state)
                | Q(groups__in=user.groups.all())
                | Q(corporations__corporation_id__in=corp_ids)
                | Q(alliances__alliance_id__in=alliance_ids)
                | Q(characters__character_id__in=char_ids)
                | Q(factions__faction_id__in=faction_ids)
            )
            .distinct()
        )

        # Missing-group targeting: flow has assign_if_missing_groups configured
        # and the user doesn't have any of those groups yet.
        user_group_ids = user.groups.values_list("pk", flat=True)
        missing_group_qs = (
            self.filter(status="published", assign_if_missing_groups__isnull=False)
            .exclude(assign_if_missing_groups__in=user_group_ids)
            .distinct()
        )

        return (positive_qs | missing_group_qs).distinct()
