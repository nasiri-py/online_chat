from django.contrib import admin

from .models import GroupChat, Message, Notification, UserOnlineStatus


admin.site.register(GroupChat)
admin.site.register(Message)
admin.site.register(Notification)
admin.site.register(UserOnlineStatus)
