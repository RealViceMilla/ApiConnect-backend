from django.apps import AppConfig


class ApiconnectappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'APIConnectApp'

    # Carga las señales para inicializar etapas, documentos y estados del BPM.
    def ready(self):
        import APIConnectApp.signals  # noqa: F401
