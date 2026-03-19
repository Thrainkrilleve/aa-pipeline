"""App Configuration"""

# Django
from django.apps import AppConfig

# Pipeline
from pipeline import __version__


class PipelineConfig(AppConfig):
    """App Config"""

    name = "pipeline"
    label = "pipeline"
    verbose_name = f"Pipeline v{__version__}"

    def ready(self) -> None:
        import pipeline.signals  # noqa: F401
