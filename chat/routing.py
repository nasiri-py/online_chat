from django.urls import path

from . import consumers


websocket_urlpatterns = [
    path('ws/group/<str:chat_id>/', consumers.GroupConsumer.as_asgi()),
]
