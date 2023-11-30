from django.urls import path

from . import consumers


websocket_urlpatterns = [
    path('ws/videocall/', consumers.VideoCallConsumer.as_asgi()),
]
