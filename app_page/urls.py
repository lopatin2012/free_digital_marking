from django.urls import path

from app_page import views

urlpatterns = [
    path('', view=views.HomePageView.as_view(), name='home'),
]