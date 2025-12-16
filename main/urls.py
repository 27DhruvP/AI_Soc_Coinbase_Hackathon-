from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('api/chat/', views.api_chat, name='api_chat'),
    path('api/snapshot/', views.api_snapshot, name='api_snapshot'),
    path('.well-known/farcaster.json', views.farcaster_manifest_view, name='farcaster-manifest'),
    path('api/webhook', views.webhook_view, name='webhook'),
]
