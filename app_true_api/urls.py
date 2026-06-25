# app_true_api/urls.py

from django.urls import path

from app_true_api import views

urlpatterns = [
    path('api/suz/refresh-token/', views.api_suz_refresh_token, name='api_suz_refresh_token'),
    path('api/suz/invalidate-token/', views.api_suz_invalidate_token, name='api_suz_invalidate_token'),
    path('api/suz/activate-device/', views.api_suz_activate_device, name='api_suz_activate_device'),
    path('api/suz/test-connection/', views.api_suz_test_connection, name='api_suz_test_connection'),
]