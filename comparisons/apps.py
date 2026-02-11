from django.apps import AppConfig


class ComparisonsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "comparisons"
    verbose_name = "Hebrew–Niger-Congo Comparisons"

    def ready(self):
        import comparisons.signals  # noqa: F401
