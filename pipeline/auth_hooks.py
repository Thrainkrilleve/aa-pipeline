"""Hook into Alliance Auth"""

# Django
from django.utils.translation import gettext_lazy as _

# Alliance Auth
from allianceauth import hooks
from allianceauth.services.hooks import MenuItemHook, UrlHook

from . import urls
from .views import pipeline_dashboard


class PipelineMenuItem(MenuItemHook):
    """Sidebar menu entry — only visible to users with basic_access."""

    def __init__(self):
        MenuItemHook.__init__(
            self,
            _("Pipeline"),
            "fas fa-route fa-fw",
            "pipeline:index",
            navactive=["pipeline:"],
        )

    def render(self, request) -> str:
        if request.user.has_perm("pipeline.basic_access"):
            return MenuItemHook.render(self, request)
        return ""


class PipelineDashboardHook(hooks.DashboardItemHook):
    def __init__(self):
        super().__init__(pipeline_dashboard, 1)


@hooks.register("menu_item_hook")
def register_menu():
    return PipelineMenuItem()


@hooks.register("url_hook")
def register_urls():
    return UrlHook(urls, "pipeline", r"^pipeline/")


@hooks.register("dashboard_hook")
def register_dashboard():
    return PipelineDashboardHook()


# ── GDPR hook (aa-gdpr integration) ─────────────────────────────────────────
# If aa-gdpr is not installed, this hook registration is silently ignored by
# the Alliance Auth hooks framework.


@hooks.register("gdpr_hook")
def register_gdpr():
    from .gdpr import PipelineGDPRHook  # late import — keeps startup clean

    return PipelineGDPRHook()
