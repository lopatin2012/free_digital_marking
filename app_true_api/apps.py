from django.apps import AppConfig


class AppTrueApiConfig(AppConfig):
    name = 'app_true_api'
    verbose_name='3. Сервис True_API'

    def ready(self):
        import app_true_api.signals

