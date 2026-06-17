# app_event/urls.py

from django.urls import path

from app_event import views

urlpatterns = [
    path('api/', view=views.get_events_api, name='api_events'),
]
