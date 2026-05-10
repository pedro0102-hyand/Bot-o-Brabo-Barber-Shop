from django.urls import path
from . import views

urlpatterns = [
    path("telegram/", views.webhook, name="telegram-webhook"),
]