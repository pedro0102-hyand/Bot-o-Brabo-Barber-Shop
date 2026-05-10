from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/chatbot/", include("apps.chatbot.urls")),
    path("api/webhook/", include("apps.webhook.urls")),
]
