from django.contrib import admin

from .models import GroupChat, Member, GroupMessage, RoomMessage


admin.site.register(GroupChat)
admin.site.register(Member)
admin.site.register(GroupMessage)
admin.site.register(RoomMessage)
