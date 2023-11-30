from django.urls import path

from . import consumers


websocket_urlpatterns = [
    path('ws/group/<str:chat_id>/', consumers.GroupConsumer.as_asgi()),
    path('ws/room/<str:username>/', consumers.RoomConsumer.as_asgi()),
    path('ws/online/', consumers.UserOnlineStatusConsumer.as_asgi()),
    path('ws/notify/', consumers.NotificationConsumer.as_asgi()),
    path('ws/seen_message/<str:slug>/', consumers.SeenMessageConsumer.as_asgi()),
]
