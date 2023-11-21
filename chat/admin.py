from django.contrib import admin

from .models import GroupChat, Member, Message, Notif, UserOnlineStatus


admin.site.register(GroupChat)
admin.site.register(Member)
admin.site.register(Message)
admin.site.register(Notif)
admin.site.register(UserOnlineStatus)
