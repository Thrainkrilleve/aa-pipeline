"""
Service Registry — runtime lookup of installed Alliance Auth service apps.

Each entry maps a slug (used in FlowStep.service_slug) to metadata needed to
check whether a user has an active account for that service.

All lookups are guarded by ``django.apps.apps.is_installed()`` so there is
*no hard dependency* on any service app.  If a service is not installed, the
check simply treats the step as not applicable (auto-pass or fall back to
acknowledgement, depending on the step configuration).

Adding a new service
--------------------
Append an entry to ``_REGISTRY`` with:

    slug       : str  — identifier used in FlowStep.service_slug
    app_label  : str  — Django app label to check with apps.is_installed()
    model_path : str  — "app_label.ModelName" for apps.get_model()
    user_field : str  — field name on the model that holds the FK to User
    name       : str  — Human-readable service name shown in the UI
    icon       : str  — Font Awesome class string (e.g. "fab fa-discord")
"""

# Standard Library
import logging

# Django
from django.apps import apps
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Registry definition
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, dict] = {
    "discord": {
        "app_label": "discord",
        "model_path": "discord.DiscordUser",
        "user_field": "user",
        "name": "Discord",
        "icon": "fab fa-discord",
    },
    "mumble": {
        "app_label": "mumble",
        "model_path": "mumble.MumbleUser",
        "user_field": "user",
        "name": "Mumble",
        "icon": "fas fa-microphone",
    },
    "teamspeak": {
        "app_label": "ts3",
        "model_path": "ts3.TeamspeakUser",
        "user_field": "user",
        "name": "TeamSpeak 3",
        "icon": "fas fa-headset",
    },
    "ips": {
        "app_label": "ips",
        "model_path": "ips.IPSUser",
        "user_field": "user",
        "name": "IPS Forum",
        "icon": "fas fa-comments",
    },
    "xenforo": {
        "app_label": "xenforo",
        "model_path": "xenforo.XenForoUser",
        "user_field": "user",
        "name": "XenForo Forum",
        "icon": "fas fa-comments",
    },
    "openfire": {
        "app_label": "openfire",
        "model_path": "openfire.OpenfireUser",
        "user_field": "user",
        "name": "Openfire XMPP",
        "icon": "fas fa-comment-dots",
    },
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def is_service_installed(slug: str) -> bool:
    """Return True if the service identified by *slug* is installed and available."""
    entry = _REGISTRY.get(slug)
    if entry is None:
        return False
    return apps.is_installed(entry["app_label"])


def check_service_for_user(slug: str, user: User) -> bool:
    """
    Return True if *user* has an active account for the service identified by *slug*.

    Returns False (not raises) on any error, including the service app not being
    installed, an unexpected model structure, or a database error.
    """
    entry = _REGISTRY.get(slug)
    if entry is None:
        logger.warning("Pipeline service registry: unknown slug %r", slug)
        return False

    if not apps.is_installed(entry["app_label"]):
        logger.debug(
            "Pipeline service registry: app %r not installed, slug %r",
            entry["app_label"],
            slug,
        )
        return False

    try:
        model = apps.get_model(entry["model_path"])
        return model.objects.filter(**{entry["user_field"]: user}).exists()
    except Exception:
        logger.exception(
            "Pipeline service registry: error checking service %r for user %s",
            slug,
            user.pk,
        )
        return False


def get_service_info(slug: str) -> dict | None:
    """Return the registry entry for *slug*, or None if not found."""
    return _REGISTRY.get(slug)


def get_all_services() -> dict[str, dict]:
    """
    Return a copy of the full registry enriched with an ``installed`` bool
    for each entry (useful in the admin builder to show what's available).
    """
    return {
        slug: {**entry, "installed": apps.is_installed(entry["app_label"])}
        for slug, entry in _REGISTRY.items()
    }
