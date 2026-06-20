from django.urls import path

from app_page import views

urlpatterns = [
    path('', view=views.HomePageView.as_view(), name='home'),
    path('test-true-api/', views.test_true_api_connection, name='test_true_api'),
]